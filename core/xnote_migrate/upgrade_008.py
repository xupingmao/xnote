# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-07-03 09:03:21
@LastEditors  : xupingmao
@LastEditTime : 2022-07-16 23:48:04
@FilePath     : /xnote/handlers/upgrade/upgrade_008.py
@Description  : 描述
"""

from .base import is_upgrade_done, mark_upgrade_done

def do_upgrade():
    upgrade_key = "upgrade_008"
    if is_upgrade_done(upgrade_key):
        return
    mark_upgrade_done(upgrade_key)

