# -*- coding:utf-8 -*-

__doc__ = """core模块的作用主要是为应用层提供一些通用的能力，包括但不限于
1、应用层(handlers模块)的模块加载
2、定时任务调度
3、账号权限控制
4、全局配置和用户配置
5、事件驱动机制
6、HTML模板引擎
7、插件的加载
8、多语言支持

core模块依赖xutils模块，xutils提供更加底层的组件能力，比如数据库、文本函数库、文件操作等等。
两者的区别是：core模块是拥有业务状态的，xutils基本没有。
"""
import sys

from . import xnote_pathfix

xnote_pathfix.fix()

from xnote.core import xconfig, xauth, autoreload, xmanager, xtemplate
from xnote.core import xnote_hooks, xnote_event, xnote_trace, xnote_app, xnote_user_config
from xnote.core import xtables, xtables_new

sys.modules["xconfig"] = xconfig
sys.modules["xauth"] = xauth
sys.modules["autoreload"] = autoreload
sys.modules["xmanager"] = xmanager
sys.modules["xtemplate"] = xtemplate
sys.modules["xnote_hooks"] = xnote_hooks
sys.modules["xnote_event"] = xnote_event
sys.modules["xnote_trace"] = xnote_trace
sys.modules["xnote_app"] = xnote_app
sys.modules["xtables"] = xtables
sys.modules["xtables_new"] = xtables_new
sys.modules["xnote_user_config"] = xnote_user_config
