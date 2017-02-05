import web
from web.py3helpers import PY2
from tornado.template import Template, Loader
import config 
import json
import sys
import traceback
from io import BytesIO

if PY2:
    from urllib import quote, urlopen
else:
    from urllib.parse import quote
    from urllib.request import urlopen
import os
import logging

from util import fsutil
from util import dateutil
from util import textutil
from util import htmlutil
from util import osutil
from util import dbutil
from util import netutil

import xtemplate
from xtemplate import render as xtemplate_render

import FileDB

_loader = Loader("template")

logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())

def print_exception(e):
    ex_type, ex, tb = sys.exc_info()
    print(ex)
    traceback.print_tb(tb)

class Undefined:

    def __getattr__(self, key):
        return self

    def __setattr__(self, key):
        raise AttributeError(key)

    def __repr__(self):
        return "undefined"

    def __str__(self):
        return "undefined"

class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.
    
        >>> o = storage(a=1)
        >>> o.a
        1
        >>> o['a']
        1
        >>> o.a = 2
        >>> o['a']
        2
        >>> del o.a
        >>> o.a
        Traceback (most recent call last):
            ...
        AttributeError: 'a'
    
    """

    undefined = Undefined()

    def __getattr__(self, key): 
        try:
            return self[key]
        except KeyError as k:
            return Storage.undefined
    
    def __setattr__(self, key, value): 
        self[key] = value
    
    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError as k:
            raise AttributeError(k)
    
    def __repr__(self):     
        return '<Storage ' + dict.__repr__(self) + '>'

def get_template_namespace():
    namespace = {}
    namespace["format_date"] = dateutil.format_date
    namespace["format_time"] = dateutil.format_time
    return namespace

def reload_template():
    xtemplate.reload()

def get_template_code(name):
    return xtemplate.get_code(name)

def parse_json_obj(obj):
    if isinstance(obj, dict):
        return Storage(obj)
    if isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = parse_json_obj(obj[i])
    return obj

def parse_json(str):
    obj = json.loads(str)
    return parse_json_obj(obj)

def get_json(url):
    print(url)
    bytes = urlopen(url).read()
    content = bytes.decode("utf-8")
    return parse_json(content)

def Result(success = True, msg=None):
    return {"success": success, "result": None, "msg": msg}
    
def ErrorResult(msg):
    return {"success":False, "result": msg}

is_iter = lambda x: x and hasattr(x, '__next__')


def render_template(template_name, **kw):
    return xtemplate.render(template_name, **kw)

class BaseHandler():

    def get(self):
        func = None
        option = self.get_argument("option", "default")
        attr = option + "_request"
        if hasattr(self, "execute"):
            func = getattr(self, "execute")
        elif hasattr(self, attr):
            func = getattr(self, attr)
        if func is None:
            func = getattr(self, option + "Request")
        ret = func()
        if isinstance(ret, dict) or isinstance(ret, list):
            self.write(json.dumps(ret))
        elif isinstance(ret, str):
            self.write(ret)
        elif isinstance(ret, bytes):
            return ret
        elif ret is None:
            pass
        else:
            self.write(str(ret))

    def GET(self):
        # check login information
        # self.check_login()
        self._response = None
        self._input = web.input()
        self._args = None
        ret = self.get()
        if self._response is not None:
            return self._response
        return ret

    def POST(self):
        return self.GET()

    def write(self, bytes):
        self._response = bytes

    def get_template_name(self):
        """get the default template name"""
        if hasattr(self, "template_name"):
            return self.template_name
        module = type(self).__module__
        path = sys.modules[module].__file__
        path = path[:-3] # remove .py
        self.template_name = path + ".html"
        return self.template_name

    def render(self, *nargs, **kw):
        if len(nargs) == 0:
            template_name = self.get_template_name()
        else:
            template_name = nargs[0]
        if self._args is not None:
            self._args.update(kw)
            kw = self._args
        text = xtemplate_render(template_name, **kw);
        self._response = text
        return text

    def get_argument(self, *args):
        key = args[0]
        if self._args is None:
            self._args = {}

        if len(args) == 1:
            value = self._input[key]
            self._args[key] = value
            return value
        else:
            v = self._input.get(key)
            if v is None:
                v = args[1]
        self._args[key] = v
        return v

    def post(self):
        self.get()

    def redirect(self, url):
        raise web.seeother(quote(url))

    def check_login(self):
        user = web.cookies().get("xuser")
        if user != "admin":
            url = web.ctx.environ.get('PATH_INFO','-')
            raise web.seeother("/login?target="+url)

        
    def get_current_user(self):
        # print self.request.uri
        try:
            user = self.get_secure_cookie("user")
            return user
        except Exception as e:
            ex_type, ex, tb = sys.exc_info()
            traceback.print_tb(tb)
            self.clear_cookie("user")
            return None
        #if not user:
            #self.redirect("/login?ret_url="+self.request.uri)
        # globals()["user"] = user
        # self.ui['user'] = user
        # return user

class BaseFileHandler(BaseHandler):

    def render(self, template, **kw):
        id = self.get_argument("id", None)
        name = self.get_argument("name", "")
        if id is not None and id != "":
            record   = FileDB.get_by_id(id)
            pathlist = FileDB.get_vpath(record)
            # kw.update("pathlist", pathlist)
            kw["pathlist"] = pathlist
        elif name != "":
            record  = FileDB.get_by_name(name)
            pathlist = FileDB.get_vpath(record)
            kw['pathlist'] = pathlist
        BaseHandler.render(self, template, **kw)