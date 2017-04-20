# encoding=utf-8

"""xnote的handle类的基类

尝试提供以下功能
 - 权限控制
 - 参数注入
 - 结果封装
 - 渲染结果json+页面非侵入式切换
 - 性能统计

相比较之下，直接写一个类来完成webpy的处理器，优点有:
 - 参数控制更简单，webpy也很简单，但是需要web.input()，相比之前self.get_argument(key, default_value)更简单实用，
    而且可以把参数回写到结果中，这个很实用
 - 结果控制多样化，当然，webpy可以通过拦截器来实现
 - 自动定位模板位置(使用子类的__file__)，webpy需要使用拦截器

正确的使用继承能够减少很多代码量，可以参考tornado的RequestHandler设计

本项目最初是使用tornado框架的，当时我准备写一个文件下载的功能，由于tornado对异步特性不了解，经常爆出finish called twice错误，
而且由于tornado的异步特性，问题久久不能定位，后面尝试了webpy，很轻松的实现了这个功能，同时也想全方位的掌握一个web服务器，
webpy实现优雅直观，所以最终选择了webpy来开发

"""

import web
from web.py3helpers import PY2
from tornado.template import Template, Loader
import config 
import json
import sys
import traceback
from io import BytesIO

import web
from web.utils import Storage

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

logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())


def get_argument(key, default_value=None):
    _input = web.ctx.get("_xnote.input")
    if _input == None:
        _input = web.input()
        web.ctx["_xnote.input"] = _input
    value = _input.get(key)
    if value is None:
        return default_value
    return value

def print_exception():
    ex_type, ex, tb = sys.exc_info()
    print(ex)
    traceback.print_tb(tb)

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

    """Xnote处理器基类"""

    def initialize(self):
        """初始化操作，在处理请求前执行"""
        pass

    def do_get(self):
        self.initialize()
        func = None

        # TODO 下面待优化
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
        self._args = None
        ret = self.do_get()
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
        """渲染到页面, 不指定template会默认渲染Python文件同名的html文件"""
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

    def get_argument(self, key, default_value=None, strip=False):
        """获取参数, 默认值不允许为None
        ~~必须使用可变参数*args, 不然没法知道调用方参数个数，因为默认值可能为None~~
        - 1个参数，没有结果抛出异常
        - 2个参数，没有结果使用默认结果
        """
        if self._args is None:
            self._args = web.input()

        if default_value == None:
            value = self._args[key]
            self._args[key] = value
        else:
            value = self._args.get(key)
            if value is None:
                value = default_value
            if isinstance(default_value, int):
                value = int(value)
        if strip and isinstance(value, str):
            value = value.strip()
        self._args[key] = value
        return value

    def redirect(self, url):
        raise web.seeother(quote(url))

    def clear_cookie(self, key):
        """清除cookie"""
        web.setcookie(key, "", expires=-1)


def get_upload_img_path(filename):
    """生成上传文件名"""
    filename = filename.replace(" ", "_")
    basename, ext = os.path.splitext(filename)
    date = dateutil.format_date(fmt="%Y/%m")
    dirname = config.DATA_PATH + "/img/" + date + "/"
    webpath = "/data/img/" + date + "/" + filename

    origin_filename = dirname + filename
    fsutil.check_create_dirs(dirname)
    fileindex = 1
    newfilename = origin_filename
    while os.path.exists(newfilename):
        name, ext = os.path.splitext(origin_filename)
        # 使用下划线，括号会使marked.js解析图片url失败
        newfilename = "{}_{}{}".format(name, fileindex, ext)
        webpath = "/data/img/{}/{}_{}{}".format(date, basename, fileindex, ext)
        fileindex+=1
    return newfilename, webpath

