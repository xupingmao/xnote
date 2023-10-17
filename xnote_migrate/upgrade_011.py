# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-03-18 14:27:00
@LastEditors  : xupingmao
@LastEditTime : 2023-10-01 00:13:54
@FilePath     : /xnote/core/xnote_migrate/upgrade_011.py
@Description  : 迁移pulgin_visit表
"""

from xutils import dbutil
from . import base
from xutils import dbutil, Storage


def do_upgrade():
    base.move_upgrade_key("upgrade_011", "20230325_plugin_log")
    base.execute_upgrade("20230325_plugin_log", do_upgrade_plugin_log)

    base.move_upgrade_key("upgrade_011.c", "20230325_search_log")
    base.execute_upgrade("20230325_search_log", do_upgrade_search_log_20230325)

def do_upgrade_plugin_log():
    db = dbutil.get_table("plugin_visit_log")
    new_db = dbutil.get_table("plugin_visit")

    for item in db.iter(limit = -1):
        assert isinstance(item, Storage)
        user = item.user
        url = item.url
        record = new_db.first_by_index("k_url", where = dict(user=user, url=url))
        if record == None:
            record = item
            new_db.insert(record)
    

def do_upgrade_search_log_20230325():
    db = dbutil.get_table("search_history")
    db.fix_user_attr = False
    
    for item in db.iter(limit = -1):
        if item.get("user") != None:
            continue
        key = item["_key"]
        user = key.split(":")[1]
        item["user"] = user
        db.update(item)
