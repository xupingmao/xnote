# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-07 21:03:13
@LastEditors  : xupingmao
@LastEditTime : 2022-08-07 17:21:43
@FilePath     : /xnote/core/a.py
@Description  : 描述
"""
import sys
import os

def fix():
    core_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(core_dir)
    lib_dir = os.path.join(project_root, "lib")

    # insert after working dir
    sys.path.insert(1, lib_dir)
    sys.path.insert(1, core_dir)


fix()
