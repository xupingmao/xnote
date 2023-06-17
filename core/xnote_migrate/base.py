# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-02-05 16:19:20
@LastEditors  : xupingmao
@LastEditTime : 2023-06-17 09:31:15
@FilePath     : /xnote/core/xnote_migrate/base.py
@Description  : 描述
"""

import xconfig
import xtables
import os
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


def execute_upgrade(key = "", fn = lambda:None):
    if is_upgrade_done(key):
        return
    fn()
    mark_upgrade_done(key)


def migrate_sqlite_table(new_table: xtables.TableProxy, old_dbname="", check_exist_func=None):
    dbpath = xconfig.FileConfig.get_db_path(old_dbname)
    if not os.path.exists(dbpath):
        return
    
    table_name = new_table.tablename
    old_db = xtables.get_db_instance(dbpath=dbpath)
    # 初始化老的表
    old_table = xtables.init_backup_table(table_name, old_db)
    total = old_table.count()
    count = 0

    def check_exist_func_default(record):
        id = record.get("id")
        return new_table.select_first(where=dict(id=id))
    
    if check_exist_func == None:
        check_exist_func = check_exist_func_default

    for batch in old_table.iter_batch():
        with new_table.transaction():
            for old_record in batch:
                count+=1
                new_reocrd = new_table.filter_record(old_record)
                is_exists = check_exist_func(new_reocrd)
                if not is_exists:
                    # 不存在
                    new_table.insert(**new_reocrd)
        print("migrate (%s): %d/%d" % (table_name, count, total))
