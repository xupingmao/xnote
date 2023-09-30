# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-07-03 09:03:21
@LastEditors  : xupingmao
@LastEditTime : 2023-09-30 22:46:41
@FilePath     : /xnote/core/xnote_migrate/upgrade_009.py
@Description  : 描述
"""
from xutils import dbutil
from . import base
from handlers.note.dao import add_history_index

def do_upgrade():
    """修复笔记历史的索引"""
    upgrade_key = "upgrade_009"
    base.execute_upgrade(upgrade_key, fix_note_history)

def fix_note_history():
    db = dbutil.get_hash_table("note_history")
    for key, value in db.iter(limit=-1):
        note_id, version = key.split(":")
        add_history_index(note_id, value.version, value)

