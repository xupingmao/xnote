# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2016/12/05
# @modified 2018/07/21 22:45:52
import os
import json
import web
import math
import inspect
import six
from tornado.template import Template, Loader
import xconfig
import xauth
import xutils
import xtables
from xutils import dateutil, quote
from xutils import ConfigParser, Storage, tojson

TEMPLATE_DIR = xconfig.HANDLERS_DIR
NAMESPACE    = dict(
    format_date = dateutil.format_date,
    format_time = dateutil.format_time,
    quote       = quote
) 

def load_menu_properties():
    """加载导航栏配置"""
    if os.path.exists("config/menu.ini"):
        path = "config/menu.ini"
    else:
        path = "config/menu.default.ini"

    menu_list = []
    cf = ConfigParser()
    cf.read(path, encoding="utf-8")
    names = cf.sections()
    for name in names:
        group = dict(title = name)
        options = cf.options(name)
        group["children"] = []
        for option in options:
            url = cf.get(name, option)
            group["children"].append(dict(name=option, url=url))
        menu_list.append(group)

    global MENU_LIST
    MENU_LIST = menu_list

class XnoteLoader(Loader):
    """定制Template Loader"""
    
    def resolve_path_old(self, name, parent_path=None):
        if parent_path and not parent_path.startswith("<") and \
            not parent_path.startswith("/") and \
                not name.startswith("/"):
            current_path = os.path.join(self.root, parent_path)
            file_dir = os.path.dirname(os.path.abspath(current_path))
            relative_path = os.path.abspath(os.path.join(file_dir, name))
            if relative_path.startswith(self.root):
                name = relative_path[len(self.root) + 1:]
        return name

    def resolve_path(self, name, parent_path=None):
        """
        tornado中的Template._get_ancestors方法会把template的路径作为parent_path参数,
        但是Loader默认的方法处理绝对路径时，不处理相对路径,参考resolve_path_old
        由于判断绝对路径是通过`/`开头，这样造成windows系统和posix系统的处理结果不一致

        统一修改为`{% extends <abspath> %}` 和 `{% include <abspath> %}`, 继承和包含的模板路径强制为全局的，
        这样做的好处是一般全局母版的位置是不变的，移动模块不需要修改母版位置，这里的`全局`也并不是真的全局，
        而是寻找母版或者include模板时不进行路径转换
        """
        # 处理默认的模板，这里hack掉
        if name == "base":
            return xconfig.BASE_TEMPLATE
        return name

def set_loader_namespace(namespace):
    """ set basic namespace """
    _loader.namespace = namespace

def get_user_agent():
    if xconfig.IS_TEST:
        return ""
    return web.ctx.env.get("HTTP_USER_AGENT")


@xutils.cache(prefix="message.count", expire=360)
def get_message_count(user):
    if user is None:
        return 0
    return xtables.get_message_table().count(where="status=0 AND user=$user", vars=dict(user=user))

def pre_render(kw):
    """模板引擎预处理过程"""
    kw["math"] = math
    kw["_is_admin"]  = xauth.is_admin()
    kw["_has_login"] = xauth.has_login()
    user_name = xauth.get_current_name() or ""
    kw["_user_name"] = user_name
    kw["_user_agent"] = get_user_agent()
    # 处理首页公告
    kw["_top_notice"] = None
    # 用于渲染其他组件
    kw["_render"] = render
    kw["Storage"] = Storage
    kw["xutils"]  = xutils
    kw["xconfig"] = xconfig
    kw["_notice_count"] = get_message_count(user_name)
    if hasattr(web.ctx, "env"):
        kw["HOST"] = web.ctx.env.get("HTTP_HOST")

    # render input
    _input = web.ctx.get("_xnote.input")
    if _input is not None:
        kw.update(_input)

def render(template_name, **kw):
    nkw = {}
    pre_render(nkw)
    nkw.update(kw)
    _input = web.input()

    if _input.get("_format") == "json":
        web.header("Content-Type", "application/json")
        return tojson(nkw)
    return _loader.load(template_name).generate(**nkw)

def render_text(text, template_name = "<string>", **kw):
    """使用模板引擎渲染文本信息
    TODO 缓存
    """
    nkw = {}
    pre_render(nkw)
    nkw.update(kw)
    template = Template(text, name=template_name, loader=_loader)
    return template.generate(**nkw)

    
def get_code(name):
    return _loader.load(name).code

def get_templates():
    return _loader.templates.copy()
    
    
def reload():
    global _loader
    _loader = XnoteLoader(TEMPLATE_DIR, namespace = NAMESPACE)

class BaseTextPlugin:
    """纯文本插件的基类"""

    template = """
{% extends base.html %}
{% block body %}

{% init error = "" %}
{% init description = "" %}
{% init input = "" %}
{% init output = "" %}

{% include "tools/base_title.html" %}

{% if description != "" %}
<pre class="col-md-12 info">
{{description}}
</pre>
{% end %}

{% if error != "" %}
<pre class="col-md-12 error">
{{error}}
</pre>
{% end %}

<form method="{{method}}">
    <textarea class="col-md-12 code" name="input" rows={{rows}}>{{input}}</textarea>
    <button>处理</button>
</form>
<pre class="col-md-12">{{output}}</pre>
{% end %}
"""

    def __init__(self):
        self.rows = 20
        self.title = "BaseTextPlugin"
        self.method = "POST"
        self.output = ""
        self.description = ""

    def write(self, text):
        self.output += text

    def writeline(self, line):
        self.output += line + "\n"

    def handle(self, input):
        raise NotImplementedError()

    def get_input(self):
        return xutils.get_argument("input", "")

    def render(self):
        input  = self.get_input()
        error  = ""
        output = ""
        try:
            output = str(self.handle(input))
        except:
            error = xutils.print_exc()
        return render_text(self.template, 
            script_name = globals().get("script_name"),
            description = self.description,
            error = error,
            title = self.title,
            method = self.method,
            rows = self.rows,
            input = input, 
            output = self.output + output)

BaseTextPage = BaseTextPlugin

reload()
