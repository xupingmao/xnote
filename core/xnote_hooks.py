# encoding=utf-8
# @author xupingmao
# @since 2023-02-26 23:50:11
# @modified 2022/04/16 18:03:13

from xutils import Storage


class HookStore:
    init_hooks = []
    reload_hooks = []

    @classmethod
    def add_init_hook(cls, func):
        if func not in cls.init_hooks:
            cls.init_hooks.append(func)
    
    @classmethod
    def add_reload_hook(cls, func):
        if func not in cls.reload_hooks:
            cls.reload_hooks.append(func)


def get_search_handler(search_type):
    """获取搜索处理器"""
    default_handler = Storage()
    default_handler.action = "/search"
    default_handler.placeholder = u"综合搜索"
    return default_handler


def get_category_name_by_code(code):
    """通过编码获取插件类目名称"""
    raise NotImplementedError("待plugin实现")


def get_init_hooks():
    return HookStore.init_hooks

def get_reload_hooks():
    return HookStore.reload_hooks

