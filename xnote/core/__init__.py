# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-10-15 21:05:55
@LastEditors  : xupingmao
@LastEditTime : 2023-10-17 23:10:23
@FilePath     : /xnote/xnote/core/__init__.py
@Description  : 描述
"""
# encoding=utf-8
# 为了兼容Python 2.x，Python 3.x是不需要这个文件的

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
import os

def _add_to_sys_path(path):
    if path not in sys.path:
        # insert after working dir
        sys.path.insert(1, path)

def fix():
    xnote_core_dir = os.path.dirname(__file__)
    xnote_dir = os.path.dirname(xnote_core_dir)
    xnote_root = os.path.dirname(xnote_dir)
    lib_dir = os.path.join(xnote_root, "lib")
    lib_dir = os.path.abspath(lib_dir)
    # insert after working dir
    _add_to_sys_path(lib_dir)

fix()


from xnote.core import xconfig, xauth, autoreload, xmanager, xtemplate
from xnote.core import xnote_hooks, xnote_event, xnote_trace, xnote_app, xnote_user_config
from xnote.core import xtables

# 兼容历史代码
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
sys.modules["xnote_user_config"] = xnote_user_config
