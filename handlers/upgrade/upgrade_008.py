# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-07-03 09:03:21
@LastEditors  : xupingmao
@LastEditTime : 2022-07-13 21:18:23
@FilePath     : /xnote/handlers/upgrade/upgrade_008.py
@Description  : 描述
"""

import logging
import xauth
from handlers.upgrade.upgrade_main import is_upgrade_done
from handlers.upgrade.upgrade_main import mark_upgrade_done
from handlers.note import dao_book

def do_upgrade():
    upgrade_key = "upgrade_008"
    mark_upgrade_done(upgrade_key)

