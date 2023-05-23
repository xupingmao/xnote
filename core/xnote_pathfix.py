# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-07 21:03:13
@LastEditors  : xupingmao
@LastEditTime : 2023-05-23 22:59:59
@FilePath     : /xnote/core/xnote_pathfix.py
@Description  : 描述
"""
import sys
import os

def set_module_alias(name, mod):
    sys.modules[name] = mod

class Fixer:
    fixed = False

def _add_to_sys_path(path):
    if path not in sys.path:
        sys.path.insert(1, path)

def fix():
    if Fixer.fixed:
        return
    
    core_dir = os.path.dirname(__file__)
    core_dir = os.path.abspath(core_dir)
    project_root = os.path.dirname(core_dir)
    lib_dir = os.path.join(project_root, "lib")

    # insert after working dir
    _add_to_sys_path(lib_dir)
    _add_to_sys_path(core_dir)

    Fixer.fixed = True

def fix_core():
    from . import xmanager, xauth, xconfig
    set_module_alias("xmanager", xmanager)
    set_module_alias("xauth", xauth)
    set_module_alias("xconfig", xconfig)

fix()
