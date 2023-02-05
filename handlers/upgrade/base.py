# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-02-05 16:19:20
@LastEditors  : xupingmao
@LastEditTime : 2023-02-05 16:19:40
@FilePath     : /xnote/handlers/upgrade/base.py
@Description  : 描述
"""

from xutils import dbutil
from xutils import dateutil

dbutil.register_table("db_upgrade_log", "数据库升级日志")
sys_log_db = dbutil.get_table("sys_log")

def get_upgrade_log_table():
    return dbutil.get_hash_table("db_upgrade_log")

def is_upgrade_done(op_flag):
    db = get_upgrade_log_table()
    return db.get(op_flag) == "1"

def mark_upgrade_done(op_flag):
    db = get_upgrade_log_table()
    db.put(op_flag, "1")

def log_info(fmt, *args):
    print(dateutil.format_time(), "[upgrade]", fmt.format(*args))

def log_error(fmt, *args):
    print(dateutil.format_time(), "[upgrade]", fmt.format(*args))

def log_warn(fmt, *args):
    print(dateutil.format_time(), "[upgrade]", fmt.format(*args))
