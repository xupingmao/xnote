# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-03-18 14:27:00
@LastEditors  : xupingmao
@LastEditTime : 2023-04-29 19:44:10
@FilePath     : /xnote/core/xnote_migrate/upgrade_011.py
@Description  : 迁移pulgin_visit表
"""

from xutils import dbutil
import xtables
from . import base
from xutils import dbutil, Storage


def do_upgrade():
    do_upgrade_plugin_log()
    do_upgrade_search_log_20230325()
    # do_upgrade_note_tag_20230520()

def do_upgrade_plugin_log():
    upgrade_key = "upgrade_011"
    if base.is_upgrade_done(upgrade_key):
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
    
    base.mark_upgrade_done(upgrade_key)

def do_upgrade_search_log_20230325():
    upgrade_key = "upgrade_011.c"
    if base.is_upgrade_done(upgrade_key):
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

    base.mark_upgrade_done(upgrade_key)

def do_upgrade_note_tag_20230520():
    key = "upgrade_011.d"

    def upgrade_func():
        db_old = dbutil.get_table("note_tags")
        target_db = xtables.get_note_tag_bind_table()

    base.execute_upgrade(key, upgrade_func)