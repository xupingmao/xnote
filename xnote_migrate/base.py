# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-02-05 16:19:20
@LastEditors  : xupingmao
@LastEditTime : 2024-06-23 22:36:59
@FilePath     : /xnote/xnote_migrate/base.py
@Description  : 描述
"""

import datetime
import os
import xutils

from xnote.core import xconfig
from xnote.core import xtables
from xutils import dbutil, Storage
from xutils import dateutil
from xutils.base import BaseDataRecord

class MigradeFailedDO(Storage):

    def __init__(self):
        self.ctime = xutils.format_datetime()
        self.table_name = ""
        self.reason = ""
        self.record = None


dbutil.register_table("db_upgrade_log", "数据库升级日志", type="hash")
sys_log_db = dbutil.get_table("sys_log")
failed_db = dbutil.get_table("migrate_failed")

class SystemUpgradeLogRecord(BaseDataRecord):
    _ignore_save_fields = ["id"]
    def __init__(self):
        timestamp = dateutil.timestamp_ms()
        self.create_time = timestamp
        self.update_time = timestamp
        self.log_key = ""
        self.log_content = ""
        self.cost_time = 0
        
    def validate(self):
        if self.log_key == "":
            raise ValueError("log_key is empty")
        if self.log_content == "":
            raise ValueError("log_content is empty")
        if len(self.log_key) > 100:
            raise ValueError("log_key is too long")

class SystemUpgradeLogDao:
    db = xtables.get_table_by_name("system_upgrade_log")
    
    @classmethod
    def delete(cls, log_key: str):
        return cls.db.delete(where = dict(log_key=log_key))
    
    @classmethod
    def get(cls, log_key: str):
        result = cls.db.select_first(where = dict(log_key=log_key))
        if result == None:
            return None
        return SystemUpgradeLogRecord.from_dict(result).log_content
    
    @classmethod
    def put(cls, log_key: str, log_content: str, cost_time: int = 0):
        log = SystemUpgradeLogRecord()
        log.log_key = log_key
        log.log_content = log_content
        log.cost_time = cost_time
        log.validate()
        values = log.to_save_dict()
        cls.db.insert(**values)

def get_upgrade_log_table():
    return SystemUpgradeLogDao

def is_upgrade_done(op_flag):
    db = get_upgrade_log_table()
    return db.get(op_flag) != None

def mark_upgrade_done(op_flag, cost_time: int = 0):
    db = get_upgrade_log_table()
    db.put(op_flag, "1", cost_time)

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
    start_time = dateutil.timestamp_ms()
    fn()
    cost_time = dateutil.timestamp_ms() - start_time
    mark_upgrade_done(key, cost_time = cost_time)

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
    """把sqlite的表从旧的数据库迁移到新的数据库"""
    dbpath = xconfig.FileConfig.get_db_path(old_dbname)
    if not os.path.exists(dbpath):
        return
    
    table_name = new_table.tablename
    old_db = xtables.get_db_instance(dbpath=dbpath)
    # 初始化老的表
    old_table = xtables.init_backup_table(table_name, old_db, dbpath=dbpath)
    total = old_table.count()
    count = 0

    def check_exist_func_default(record: dict):
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


def is_valid_datetime(value):
    try:
        dateutil.parse_datetime(value)
        return True
    except:
        return False


def is_valid_int(value):
    try:
        int(value)
        return True
    except:
        return False


def validate_datetime(value):
    if value == "":
        raise Exception("invalid datetime")
    return dateutil.parse_datetime(value)