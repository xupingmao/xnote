# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2021/01/17 10:51:22
# @modified 2021/11/07 12:53:19

from http.server import BaseHTTPRequestHandler
import profile
import time
import web
import math
from xutils.six import BytesIO
from web import utils

#################################################################
##   Web.py Utilities web.py工具类的封装
#################################################################

IS_TEST = False
MOBILE_UA_NAMES = ("iphone", "android", "ipad", "webos")


def print_web_ctx_env():
    for key in web.ctx.env:
        print(" - - %-20s = %s" % (key, web.ctx.env.get(key)))

def get_web_ctx_env():
    return web.ctx.env

def _get_default_by_type(default_value, type):
    if default_value != None:
        return default_value
    if type is bool:
        return False
    return None

def _detect_type(default_value, type):
    """根据默认值+类型检测类型"""
    if type != None:
        return type
    
    if isinstance(default_value, bool):
        return bool
    
    if isinstance(default_value, int):
        return int
    
    if isinstance(default_value, float):
        return float
    
    return None

def get_argument(key, default_value=None, type = None, strip=False):
    """获取请求参数
    @param {string} key 请求的参数名
    @param {object} default_value 默认值
    @param {type} type 参数类型
    @param {bool} strip 是否过滤空白字符
    """
    if not hasattr(web.ctx, "env"):
        if default_value != None:
            return default_value
        return None
    ctx_key = "_xnote.input"
    if isinstance(default_value, (dict, list)):
        return web.input(**{key: default_value}).get(key)
    _input = web.ctx.get(ctx_key)
    if _input == None:
        _input = web.input()
        web.ctx[ctx_key] = _input
    value = _input.get(key)

    if value is None or value == "":
        default_value = _get_default_by_type(default_value, type)
        _input[key] = default_value
        return default_value
    
    # 检测参数类型
    type = _detect_type(default_value, type)

    if type == bool:
        # bool函数对非空字符串都默认返回true，需要处理一下
        value = value.lower() in ("true", "yes", "y", "on")
        _input[key] = value
    elif type != None:
        value = type(value)
        _input[key] = value
    
    if strip and isinstance(value, str):
        value = value.strip()
    
    return value

def get_argument_str(key: str, default_value = "") -> str:
    """获取字符串参数"""
    value = get_argument(key, default_value, type = str, strip = True)
    assert isinstance(value, str)
    return value

def get_argument_int(key: str, default_value = 0) -> int:
    """获取int参数"""
    value = get_argument(key, default_value=default_value, type = int, strip = True)
    assert isinstance(value, int)
    return value

def get_argument_float(key: str, default_value = 0.0) -> float:
    """获取float参数"""
    value = get_argument(key, default_value=default_value, type = float, strip = True)
    assert isinstance(value, float)
    return value

def get_argument_bool(key: str, default_value = False) -> bool:
    """获取bool参数"""
    value = get_argument(key, default_value=default_value, type = bool, strip = True)
    assert isinstance(value, bool)
    return value

def get_argument_dict(key="", default_value={}):
    """获取dict类型的参数"""
    value = get_argument(key=key, default_value=default_value)
    if not isinstance(value, dict):
        raise Exception("expect dict but see %s" % type(value))
    return value

def get_argument_field_storage(key=""):
    import cgi
    value = get_argument(key=key, default_value={})
    assert isinstance(value, cgi.FieldStorage)
    return value


def get_client_user_agent():
    if IS_TEST:
        return ""
    return web.ctx.env.get("HTTP_USER_AGENT")

def get_client_platform(user_agent = None):
    if user_agent is None:
        user_agent = get_client_user_agent()

    if user_agent is None:
        return False

    user_agent_lower = user_agent.lower()
    for name in MOBILE_UA_NAMES:
        if user_agent_lower.find(name) >= 0:
            return "mobile"
    return "desktop"


def is_mobile_client(user_agent = None):
    """通过UA判断是否是移动客户端
    @param {str|None} user_agent 浏览器标识（可选）
    """
    return get_client_platform(user_agent) == "mobile"


def is_desktop_client(user_agent = None):
    return get_client_platform(user_agent) == "desktop"

def get_real_ip():
    x_forwarded_for = web.ctx.env.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for != None:
        return x_forwarded_for.split(",")[0]
    return web.ctx.env.get("REMOTE_ADDR")

def get_client_ip():
    return get_real_ip()


def get_request_url(host=False):
    # TODO 待测试
    return web.ctx.path + "?" + web.ctx.query

def get_request_path():
    return web.ctx.path

class LogMiddleware:
    """WSGI middleware for logging the status.

    中间件的实现参考 web/httpservers.py
    """

    PROFILE_SET = set()

    def __init__(self, app):
        self.app = app
        self.format = '%s - - [%s] "%s %s %s" - %s %s ms'

        f = BytesIO()

        class FakeSocket:

            def makefile(self, *a):
                return f

        # take log_date_time_string method from BaseHTTPRequestHandler
        self.log_date_time_string = BaseHTTPRequestHandler(
            FakeSocket(), None, None).log_date_time_string

    def invoke_app(self, environ, start_response):
        start_time = time.time()

        def xstart_response(status, response_headers, *args):
            out = start_response(status, response_headers, *args)
            self.log(status, environ, time.time() - start_time)
            return out

        return self.app(environ, xstart_response)

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '_')
        if path in LogMiddleware.PROFILE_SET:
            vars = dict(f=self.invoke_app,
                        environ=environ,
                        start_response=start_response)
            profile.runctx("r=f(environ, start_response)",
                           globals(),
                           vars,
                           sort="time")
            return vars["r"]
        else:
            return self.invoke_app(environ, start_response)

    def log(self, status, environ, cost_time):
        outfile = environ.get('wsgi.errors', web.debug)
        req = environ.get('PATH_INFO', '_')
        query_string = environ.get("QUERY_STRING", '')
        if query_string != '':
            req += '?' + query_string
        protocol = environ.get('ACTUAL_SERVER_PROTOCOL', '-')
        method = environ.get('REQUEST_METHOD', '-')
        x_forwarded_for = environ.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for is not None:
            host = x_forwarded_for.split(",")[0]
        else:
            host = "%s:%s" % (environ.get(
                'REMOTE_ADDR', '-'), environ.get('REMOTE_PORT', '-'))

        time = self.log_date_time_string()

        msg = self.format % (host, time, protocol, method, req, status,
                             int(1000 * cost_time))
        print(utils.safestr(msg), file=outfile)

def init_webutil_env(is_test = False):
    global IS_TEST
    IS_TEST = is_test


class SuccessResult(web.Storage):

    def __init__(self, data=None, message=""):
        self.success = True
        self.code = "success"
        self.data = data


class FailedResult(web.Storage):

    def __init__(self, code="500", message=""):
        self.success = False
        self.code = code
        self.message = message


class Pagination:
    
    def __init__(self, page=1, total=0, page_size=20):
        self.page = page
        self.total = total
        self.page_max = int(math.ceil(total/page_size))
        if self.page_max == 0:
            self.page_max = 1

        