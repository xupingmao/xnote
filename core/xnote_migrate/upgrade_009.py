# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-07-03 09:03:21
@LastEditors  : xupingmao
@LastEditTime : 2023-10-01 00:38:05
@FilePath     : /xnote/core/xnote_migrate/upgrade_009.py
@Description  : 描述
"""
import xutils
from xutils import dbutil
from . import base
from handlers.note.dao import add_history_index

def do_upgrade():
    """修复笔记历史的索引"""
    base.move_upgrade_key("upgrade_009", "20220703_fix_note_history")
    base.execute_upgrade("20220703_fix_note_history", fix_note_history)

class NoteHistoryDO(xutils.Storage):

    def __init__(self, **kw):
        self.version = 0
        self.name = ""
        self.mtime = ""
        self.update(kw)


def fix_note_history():
    db = dbutil.get_hash_table("note_history")
    for key, _value in db.iter(limit=-1):
        value = NoteHistoryDO(**_value)
        note_id, version = key.split(":")
        add_history_index(note_id, value.version, value)

