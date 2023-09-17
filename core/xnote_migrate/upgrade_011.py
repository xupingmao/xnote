# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-03-18 14:27:00
@LastEditors  : xupingmao
@LastEditTime : 2023-09-17 11:46:35
@FilePath     : /xnote/core/xnote_migrate/upgrade_011.py
@Description  : 迁移pulgin_visit表
"""

from xutils import dbutil
from . import base
from xutils import dbutil, Storage


def do_upgrade():
    do_upgrade_plugin_log()
    do_upgrade_search_log_20230325()

def do_upgrade_plugin_log():
    new_key = "20230325_plugin_log"
    if base.is_upgrade_done(new_key):
        return
    
    upgrade_key = "upgrade_011"
    if base.is_upgrade_done(upgrade_key):
        base.mark_upgrade_done(new_key)
        base.get_upgrade_log_table().delete(upgrade_key)
        return

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
    
    base.mark_upgrade_done(new_key)

def do_upgrade_search_log_20230325():
    new_key = "20230325_search_log"
    
    if base.is_upgrade_done(new_key):
        return

    upgrade_key = "upgrade_011.c"
    if base.is_upgrade_done(upgrade_key):
        base.mark_upgrade_done(new_key)
        base.get_upgrade_log_table().delete(upgrade_key)
        return
    
    db = dbutil.get_table("search_history")
    db.fix_user_attr = False
    
    for item in db.iter(limit = -1):
        if item.get("user") != None:
            continue
        key = item["_key"]
        user = key.split(":")[1]
        item["user"] = user
        db.update(item)

    base.mark_upgrade_done(new_key)
