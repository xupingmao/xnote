#coding=utf-8

'''
Tornado template wrapper
Created by xupingmao on 2016/12/05
'''

import web

from tornado.template import Template, Loader
from util import dateutil

import config
import xauth

TEMPLATE_DIR = config.HANDLERS_DIR
NAMESPACE    = dict(
    format_date = dateutil.format_date,
    format_time = dateutil.format_time
)    

_hooks = []


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

def pre_render(kw):
    """ Main hook for template engine """
    kw["_full_search"] = False
    kw["_search_type"] = "normal"
    # TODO prevent hack
    kw["_is_admin"] = xauth.is_admin()
    kw["_has_login"] = xauth.has_login()
    kw["_user"] = xauth.get_current_user()
    # kw["_notice_list"] = ["Hello", "Just Try"]
    # TODO 处理首页公告
    kw["_notice_list"] = []
    # print(web.ctx.env)
    kw["_user_agent"] = web.ctx.env.get("HTTP_USER_AGENT")


def render(template_name, **kw):
    nkw = {}
    pre_render(nkw)
    nkw.update(kw)
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
    
    
def reload():
    global _loader
    _loader = XnoteLoader(TEMPLATE_DIR, namespace = NAMESPACE)
    
reload()
