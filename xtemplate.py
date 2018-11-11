# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2016/12/05
# @modified 2018/11/11 16:28:13
import os
import json
import web
import math
import inspect
import six
import xconfig
import xauth
import xutils
import xtables
from tornado.template import Template, Loader
from xutils import dateutil, quote
from xutils import ConfigParser, Storage, tojson

TEMPLATE_DIR = xconfig.HANDLERS_DIR
NAMESPACE    = dict(
    format_date = dateutil.format_date,
    format_time = dateutil.format_time,
    quote       = quote
)

_lang_dict = dict()

def load_languages():
    global _lang_dict

    _lang_dict.clear()
    dirname = xconfig.LANG_DIR
    for fname in os.listdir(dirname):
        name, ext = os.path.splitext(fname)
        if ext != ".properties":
            continue
        fpath   = os.path.join(dirname, fname)
        content = xutils.readfile(fpath)
        config  = xutils.parse_config_text(content)
        mapping = dict()
        for item in config:
            mapping[item['key']] = item['value']
        _lang_dict[name] = mapping


def T(text, lang = None):
    if lang is None:
        lang = web.ctx.get('_lang', 'zh')
    mapping = _lang_dict.get(lang)
    if mapping is None:
        return text
    else:
        return mapping.get(text, text)

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
    kw["math"]          = math
    kw["_is_admin"]     = xauth.is_admin()
    kw["_has_login"]    = xauth.has_login()
    user_name           = xauth.get_current_name() or ""
    kw["_user_name"]    = user_name
    kw["_user_agent"]   = get_user_agent()
    # 处理首页公告
    kw["_top_notice"]   = None
    # 用于渲染其他组件
    kw["_render"]       = render
    kw["Storage"]       = Storage
    kw["xutils"]        = xutils
    kw["xconfig"]       = xconfig
    kw["_notice_count"] = get_message_count(user_name)
    kw["T"]             = T
    if hasattr(web.ctx, "env"):
        kw["HOST"] = web.ctx.env.get("HTTP_HOST")
        # 语言环境
        web.ctx._lang = web.cookies().get("lang", "zh")

    if xutils.sqlite3 is None:
        kw["warn"] = "WARN: sqlite3不可用"

    # render input
    _input = web.ctx.get("_xnote.input")
    if _input is not None:
        kw.update(_input)

def render(template_name, **kw):
    nkw = {}
    pre_render(nkw)
    nkw.update(kw)

    if hasattr(web.ctx, "env"):
        # 不一定是WEB过来的请求
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
    """reload template manager"""
    global _loader
    _loader = XnoteLoader(TEMPLATE_DIR, namespace = NAMESPACE)
    _loader.reset()
    load_languages()

class BasePlugin:
    """插件的基类"""

    # 插件的标题
    title = "PluginName"
    description = ""
    # 默认需要管理员权限访问
    require_admin = True

    def __init__(self):
        # 输入框的行数
        self.rows            = 20    
        self.btn_text        = "处理"
        # 提交请求的方法
        self.method          = "POST"
        self.output          = ""
        self.html            = ""
        self.css_style       = ""
        self.show_pagenation = False
        self.page_url        = "?page="
        self.aside_html      = ""
        self.option_links    = []
        self.show_aside      = False
        
    def add_option_link(name, url):
        self.option_links.append(dict(name=name, url = url))

    def write(self, text):
        self.output += text

    def writeline(self, line):
        self.output += line + "\n"

    def writehtml(self, html):
        self.html += html

    def handle(self, input):
        raise NotImplementedError()

    def get_input(self):
        return xutils.get_argument("input", "")

    def get_format(self):
        """返回当前请求的数据格式"""
        return xutils.get_argument("_format", "")

    def get_page(self):
        """返回当前页码"""
        return xutils.get_argument("page", 1, type=int)

    def render(self):
        if self.require_admin:
            xauth.check_login("admin")
        input  = self.get_input()
        error  = ""
        output = ""
        try:
            self.page = self.get_page()
            output = self.handle(input) or ""
            if self.get_format() == "text":
                web.header("Content-Type", "text/plain; charset:utf-8")
                return self.output + output

            # 复杂对象交给框架处理
            if isinstance(output, (dict, list)):
                return output

            # 处理侧边栏显示
            if self.aside_html != "" or len(self.option_links) > 0:
                self.show_aside = True
        except:
            error = xutils.print_exc()
        return render("plugins/text.html",
            model       = self,
            script_name = globals().get("script_name"),
            description = self.description,
            error       = error,
            html_title  = self.title,
            title       = self.title,
            method      = self.method,
            rows        = self.rows,
            input       = input, 
            output      = self.output + output,
            css_style   = self.css_style,
            show_aside  = self.show_aside,
            html        = self.html)

    def on_install(self, context=None):
        """安装插件事件, TODO"""
        pass

    def on_uninstall(self, context=None):
        """卸载插件事件, TODO"""
        pass

    def on_init(self, context=None):
        """系统初始化事件"""
        pass

    def on_event(self, event):
        """其他事件"""
        pass

    def GET(self):
        return self.render()

    def POST(self):
        return self.render()

BaseTextPage   = BasePlugin
BaseTextPlugin = BasePlugin

reload()
