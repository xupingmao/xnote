# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2021/01/17 10:51:22
# @modified 2021/11/07 12:53:19

import web

#################################################################
##   Web.py Utilities web.py工具类的封装
#################################################################

IS_TEST = False
MOBILE_UA_NAMES = ("iphone", "android", "webos")


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

def get_argument(key, default_value=None, type = None, strip=False):
    """获取请求参数
    @param {string} key 请求的参数名
    @param {object} default_value 默认值
    @param {type} type 参数类型
    @param {bool} strip 是否过滤空白字符
    """
    if not hasattr(web.ctx, "env"):
        return default_value or None
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
    if type == bool:
        # bool函数对非空字符串都默认返回true，需要处理一下
        value = value in ("true", "True", "yes", "Y", "on")
        _input[key] = value
    elif type != None:
        value = type(value)
        _input[key] = value
    if strip and isinstance(value, str):
        value = value.strip()
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

def init_webutil_env(is_test = False):
    global IS_TEST
    IS_TEST = is_test

