# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-07-03 09:03:21
@LastEditors  : xupingmao
@LastEditTime : 2024-06-23 10:10:40
@FilePath     : /xnote/xnote_migrate/upgrade_008.py
@Description  : 描述
"""

from . import base

def do_upgrade():
    old_key = "upgrade_008"
    new_key = "20220703_do_nothing"
    base.move_upgrade_key(old_key, new_key)
    base.execute_upgrade(new_key, do_nothing)

def do_nothing():
    return


