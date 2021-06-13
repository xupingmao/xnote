# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/06/12 16:53:55
# @modified 2021/06/12 17:08:04
# @filename funcutil.py
import warnings

_FUNC_DICT = dict()
def register_func(name, func):
    """注册函数
    @param {string} name 函数名称，格式为 [protocol:] + [module] + name
    @param {func} func 函数
    """
    if name in _FUNC_DICT:
        warnings.warn("[register_func] name registered: %s" % name)
    _FUNC_DICT[name] = func

def call(func_name, *args, **kw):
    """调用函数
    @param {string} func_name 方法名
    @param {nargs} *args 可变参数
    @param {kwargs} **kw 关键字参数
    """
    func = lookup_func(func_name)
    if func is None:
        raise Exception("[xutils.call] func not found: %s" % func_name)
    return func(*args, **kw)

def lookup_func(func_name):
    return _FUNC_DICT.get(func_name)

def get_func_dict():
    return _FUNC_DICT.copy()

class Module:
    """Module封装"""
    def __init__(self, domain):
        self.domain = domain
        self._meth  = dict()

    def __getattr__(self, key):
        func = self._meth.get(key)
        if func:
            return func

        if key == "__wrapped__":
            return None
            
        func_name = self.domain + "." + key
        func = _FUNC_DICT[func_name]
        self._meth[key] = func
        return func

# DAO是模块的别名
class DAO(Module):
    pass
