#coding=utf-8
'''
Tornado template wrapper
Created by xupingmao on 2016/12/05
Modified by xupingmao on 2017/12/24
'''
import os
import json
import web
import math
import inspect
import six
from tornado.template import Template, Loader
from util import dateutil
import xconfig
import xauth
import xutils
import xtables
from xutils import ConfigParser, Storage

TEMPLATE_DIR = xconfig.HANDLERS_DIR
NAMESPACE    = dict(
    format_date = dateutil.format_date,
    format_time = dateutil.format_time
)    

_hooks = []

# 系统菜单
MENU_LIST = [
    # 系统管理
    Storage(category="SYS_TOOLS", admin=True, name="文件管理", url="/fs_data"),
    Storage(category="SYS_TOOLS", admin=True, name="脚本管理", url="/system/script_admin"),

    # 知识库
    Storage(category="DOC_TOOLS", login=True, name="标签云", url="/file/taglist"),

    # 开发工具
    Storage(category="DEV_TOOLS", url="/tools/date.html"),

    # 图片处理工具
    Storage(category="IMG_TOOLS", name="图片合并", url="/tools/img_merge"),

    # 编解码工具
    Storage(category="CODE_TOOLS", url="")
]

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
        return name 

def set_loader_namespace(namespace):
    """ set basic namespace """
    _loader.namespace = namespace

def add_render_hook(hook):
    _hooks.append(hook)

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
    kw["xutils"]  = xutils
    kw["xconfig"] = xconfig
    kw["_notice_count"] = get_message_count(user_name)
    if hasattr(web.ctx, "env"):
        kw["HOST"] = web.ctx.env.get("HTTP_HOST")

    # render input
    _input = web.ctx.get("_xnote.input")
    if _input is not None:
        kw.update(_input)


def encode_json(obj):
    if hasattr(obj, "__call__"):
        return "<function>"
    elif inspect.ismodule(obj):
        return "<module>"
    return obj

def render(template_name, **kw):
    nkw = {}
    pre_render(nkw)
    nkw.update(kw)
    _input = web.input()

    if _input.get("_type") == "json":
        web.header("Content-Type", "application/json")
        return json.dumps(nkw, default=encode_json)
    return _loader.load(template_name).generate(**nkw)

def render_text(text, template_name = "<string>", **kw):
    """使用模板引擎渲染文本信息"""
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
    
reload()
