# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-01-25 22:37:52
@LastEditors  : xupingmao
@LastEditTime : 2024-06-23 10:15:00
@FilePath     : /xnote/xnote_migrate/upgrade_000.py
@Description  : 描述
"""

"""升级的demo"""

from . import base
from .base import SystemUpgradeLogDao
from xutils import dbutil

def do_upgrade():
    # 先迁移升级日志
    base.execute_upgrade("20260516_migrate_upgrade_log", migrate_upgrade_log)
    
    old_key = "upgrade_000"
    new_key = "20210101_demo"
    base.move_upgrade_key(old_key, new_key)
    base.execute_upgrade(new_key, upgrade_func)

def upgrade_func():
    base.log_info("this is upgrade demo")


def migrate_upgrade_log():
    old_db = dbutil.get_hash_table("db_upgrade_log")
    for key, value in old_db.iter(limit=-1):
        log_content = SystemUpgradeLogDao.get(key)
        if log_content != None:
            continue
        SystemUpgradeLogDao.put(key, value)
