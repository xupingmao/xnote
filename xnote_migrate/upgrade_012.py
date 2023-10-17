# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-05-20 22:54:35
@LastEditors  : xupingmao
@LastEditTime : 2023-06-22 17:57:52
@FilePath     : /xnote/core/xnote_migrate/upgrade_012.py
@Description  : 描述
"""

from xutils import dbutil, Storage
from . import base
import xauth
import xtables
import xconfig
import os
from xutils import sqldb

def do_upgrade():
    base.execute_upgrade("012.1", migrate_user_20230520)
    base.execute_upgrade("012.uv", migrate_uv_log_20230528)
    base.execute_upgrade("012.dict", migrate_dict_20230610)

def get_old_dict_table():
    dbpath = xconfig.FileConfig.get_db_path("dictionary")
    db = xtables.get_db_instance(dbpath)
    table_name = "dictionary"
    with xtables.TableManager(table_name, db = db, is_backup=True) as manager:
        manager.add_column("ctime", "datetime", "1970-01-01 00:00:00")
        manager.add_column("mtime", "datetime", "1970-01-01 00:00:00")
        manager.add_column("key", "varchar(100)", "")
        manager.add_column("value", "text", "")
        manager.add_index("key")
    return sqldb.TableProxy(db, table_name)

def migrate_dict_20230610():
    dbpath = xconfig.FileConfig.get_db_path("dictionary")
    if not os.path.exists(dbpath):
        return
    old_db = get_old_dict_table()
    new_db = xtables.get_dict_table()
    count = 0
    for batch in old_db.iter_batch():
        with new_db.transaction():
            for item in batch:
                old = new_db.select_first(where=dict(id=item.id))
                if old == None:
                    item = new_db.filter_record(item)
                    new_db.insert(**item)
                    count += 1
            print("migrate dict: %d" % count)

    # xtables.move_sqlite_to_backup("dictionary")

def migrate_user_20230520():
    old_db = dbutil.get_table("user")

    for item in old_db.iter(limit=-1):
        user_dict = Storage()

        user_dict.name = item.name
        user_dict.password = item.password
        user_dict.salt = item.salt
        user_dict.login_time = item.get("login_time", "1970-01-01 00:00:00")
        user_dict.mtime = item.get("mtime", "1970-01-01 00:00:00")
        user_dict.ctime = item.get("ctime", "1970-01-01 00:00:00")
        
        record = xauth.UserModel.get_by_name(item.name)
        if record == None:
            new_user = xauth.UserDO.from_dict(user_dict)
            xauth.UserModel.create(new_user)
        else:
            record.update(user_dict)
            xauth.UserModel.update(record)

def migrate_uv_log_20230528():
    old_db = dbutil.get_table("uv")
    new_db = xtables.get_table_by_name("site_visit_log")

    for item in old_db.iter(limit=-1):
        uv_record = Storage()
        uv_record.date = item.get("date", "1970-01-01")
        uv_record.ip = item.get("ip", "")
        uv_record.site = item.get("site", "")
        uv_record.count = item.get("count", 0)
        new_db.insert(**uv_record)