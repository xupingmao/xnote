# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-02-05 16:19:20
@LastEditors  : xupingmao
@LastEditTime : 2023-09-10 11:46:41
@FilePath     : /xnote/core/xnote_migrate/base.py
@Description  : 描述
"""

import xconfig
import xtables
import os
import xutils
from xutils import dbutil, Storage
from xutils import dateutil

class MigradeFailedDO(Storage):

    def __init__(self):
        self.ctime = xutils.format_datetime()
        self.table_name = ""
        self.reason = ""
        self.record = None


dbutil.register_table("db_upgrade_log", "数据库升级日志")
sys_log_db = dbutil.get_table("sys_log")
failed_db = dbutil.get_table("migrate_failed")

def get_upgrade_log_table():
    return dbutil.get_hash_table("db_upgrade_log")

def is_upgrade_done(op_flag):
    db = get_upgrade_log_table()
    return db.get(op_flag) == "1"

def mark_upgrade_done(op_flag):
    db = get_upgrade_log_table()
    db.put(op_flag, "1")

def delete_old_flag(op_flag):
    db = get_upgrade_log_table()
    db.delete(op_flag)

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

def move_upgrade_key(old_key="", new_key=""):
    """迁移升级的key,用于统一规范"""
    if is_upgrade_done(old_key):
        mark_upgrade_done(new_key)
        delete_old_flag(old_key)

def add_failed_log(table_name="", record=None, reason=""):
    failed_obj = MigradeFailedDO()
    failed_obj.table_name = table_name
    failed_obj.record = record
    failed_obj.reason = reason
    failed_db.insert(failed_obj)


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
