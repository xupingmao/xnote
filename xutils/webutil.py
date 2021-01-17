# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2021/01/17 10:51:22
# @modified 2021/01/17 10:52:18

import web

#################################################################
##   Web.py Utilities web.py工具类的封装
#################################################################

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
        # bool函数对飞空字符串都默认返回true，需要处理一下
        value = value in ("true", "True", "yes", "Y", "on")
        _input[key] = value
    elif type != None:
        value = type(value)
        _input[key] = value
    if strip and isinstance(value, str):
        value = value.strip()
    return value

