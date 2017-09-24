#coding=utf-8

'''
Tornado template wrapper
Created by xupingmao on 2016/12/05
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

from xutils import ConfigParser

TEMPLATE_DIR = xconfig.HANDLERS_DIR
NAMESPACE    = dict(
    format_date = dateutil.format_date,
    format_time = dateutil.format_time
)    

_hooks = []

MENU_LIST = [
    
    dict(title = "资料", children = [
        dict(name="最近编辑", url="/file/recent_edit"),
        dict(name="周报", url="/search/search?key=周报"),
    ]),

    dict(title = "系统", children = [
        dict(name="系统", url="/system/sys")
    ]),

    dict(title = "功能", children = [
        dict(name="Index", url="/wiki/tools.md"),
        dict(name="日历", url="/tools/date.html"),
    ])

]

def load_menu_properties():
    """加载导航栏配置"""
    if os.path.exists("config/menu.ini"):
        path = "config/menu.ini"
    else:
        path = "config/menu.default.ini"

    menu_list = [];
    # menu_config = config.Properties(path)
    # for title in menu_config.get_properties():
    #     group = dict(title=title)
    #     group["children"] = []
    #     children = menu_config.get_properties()[title]
    #     for item in children:
    #         url = children[item]
    #         group["children"].append(dict(name=item, url=url))
    #     menu_list.append(group)

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
        """tornado中的Template._get_ancestors方法会把template的路径作为parent_path参数,
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

def pre_render(kw):
    """ Main hook for template engine """
    kw["math"] = math
    kw["_is_admin"]  = xauth.is_admin()
    kw["_has_login"] = xauth.has_login()
    kw["_user"]      = xauth.get_current_user()
    kw["_user_agent"] = get_user_agent()
    # 处理首页公告
    kw["_top_notice"] = None
    # print(web.ctx.env)
    # kw["_nav_position"] = web.cookies(nav_position="top").nav_position
    kw["_nav_position"] = "top"
    kw["_menu_list"]    = MENU_LIST
    # 用于渲染其他组件
    kw["_render"] = render
    if hasattr(web.ctx, "env"):
        kw["HOST"] = web.ctx.env.get("HTTP_HOST")

    # render input
    _input = web.ctx.get("_xnote.input")
    if _input is not None:
        kw.update(_input)


def encode_json(obj):
    if hasattr(obj, "__call__"):
        return str(obj)
    elif inspect.ismodule(obj):
        return str(obj)
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

def render_text(text, **kw):
    nkw = {}
    pre_render(nkw)
    nkw.update(kw)
    # TODO 需要优化
    template = Template(text, name="<string>", loader=_loader)
    return template.generate(**nkw)

    
def get_code(name):
    return _loader.load(name).code

def get_templates():
    return _loader.templates.copy()
    
    
def reload():
    global _loader
    _loader = XnoteLoader(TEMPLATE_DIR, namespace = NAMESPACE)
    # load_menu_properties()
    
reload()
