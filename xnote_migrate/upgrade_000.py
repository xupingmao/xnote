# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-01-25 22:37:52
@LastEditors  : xupingmao
@LastEditTime : 2023-09-30 22:34:37
@FilePath     : /xnote/core/xnote_migrate/upgrade_000.py
@Description  : 描述
"""

"""升级的demo"""

from . import base

def do_upgrade():
    mark_flag = "20210101_demo"
    base.execute_upgrade(mark_flag, upgrade_func)

def upgrade_func():
    base.log_info("this is upgrade demo")
