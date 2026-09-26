# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2026-09-26 00:09:47
@LastEditors  : xupingmao
@LastEditTime : 2026-09-26 00:09:47
@FilePath     : /xnote/xnote/plugin/router.py
@Description  : 路由插件基类，通过 query 参数把请求路由到其他插件 / 子视图，支持模式匹配。
"""

import re
import xutils

from typing import List, Optional, Type
from .base import BasePluginV2
from .plugin import PluginContext
from xnote.webui import TextSpan


class _HelloHandler(BasePluginV2):
    def handle(self, input=""):
        self.writetext("hello")

class _HelpHandler(BasePluginV2):
    def handle(self, input=""):
        self.add_component(TextSpan(text="默认的实现类", css_class="info"))
        return

class _PluginInfo:
    def __init__(self, pattern: str, plugin_class: Type[BasePluginV2]):
        self.pattern = pattern
        self.re_pattern = re.compile(pattern)
        self.plugin_class = plugin_class

class BaseRouterPlugin(BasePluginV2):
    """路由插件基类: 通过 query 参数 (默认 action) 把请求路由到不同的子视图插件,
    子视图插件也是 BasePluginV2 的子类, 路由 pattern 使用 re.match 前缀匹配"""

    # 所有路由都未命中时使用的兜底插件类
    default_handler: Type[BasePluginV2] = _HelpHandler
    # 路由表, 注意子类会共享基类的这个列表, 子类应定义自己的 handlers = []
    handlers: List[_PluginInfo] = []
    # 路由参数名
    route_param_name = "action"

    @classmethod
    def add_handler(cls, pattern: str, plugin_class: Type[BasePluginV2]):
        for item in cls.handlers:
            if item.pattern == pattern and item.plugin_class is plugin_class:
                # 避免重复注册 (on_init 可能被多次调用)
                return
        cls.handlers.append(_PluginInfo(pattern, plugin_class))

    def on_init(self, context: Optional[PluginContext] = None):
        """子类在这里注册路由"""
        return super().on_init(context)

    def handle(self, input=""):
        action = xutils.get_argument_str(self.route_param_name, "")
        for item in self.handlers:
            if item.re_pattern.match(action):
                return self.handle_sub_plugin(item.plugin_class())

        # 未命中任何路由, 使用兜底插件
        return self.handle_sub_plugin(self.default_handler())


class ExampleRouterPlugin(BaseRouterPlugin):

    require_admin = True
    title = "路由插件示例"
    handlers = []  # 避免与基类共享路由表

    def on_init(self, context: Optional[PluginContext] = None):
        self.add_handler(r"hello", _HelloHandler)
        self.default_handler = _HelpHandler

__all__ = [
    "BaseRouterPlugin",
]
