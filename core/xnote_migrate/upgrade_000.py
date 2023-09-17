# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-01-25 22:37:52
@LastEditors  : xupingmao
@LastEditTime : 2023-09-17 11:48:13
@FilePath     : /xnote/core/xnote_migrate/upgrade_000.py
@Description  : 描述
"""

"""升级的demo"""

from . import base

def do_upgrade():
    mark_flag = "20210101_demo"
    mark_flag_old = "upgrade_000"
    if base.is_upgrade_done(mark_flag):
        return
    
    if base.is_upgrade_done(mark_flag_old):
        base.mark_upgrade_done(mark_flag)
        base.get_upgrade_log_table().delete(mark_flag_old)
        return
    
    base.log_info("this is upgrade demo")
    base.mark_upgrade_done(mark_flag)