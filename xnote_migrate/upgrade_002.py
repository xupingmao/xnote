# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/31 23:22:49
# @modified 2022/01/01 23:00:39
# @filename upgrade_002.py

"""note_index索引重建"""

import xutils
from xutils import dbutil
from xutils import dateutil
from . import base

def do_upgrade():
    """升级入口"""
    old_flag = "upgrade_002"
    new_flag = "20220101_public_note"

    base.move_upgrade_key(old_key=old_flag, new_key=new_flag)
    base.execute_upgrade(new_flag, fix_note_public)

def log_info(fmt, *args):
    print(dateutil.format_time(), "[upgrade]", fmt.format(*args))

class NoteIndex(xutils.Storage):
    def __init__(self, **kw):
        self.id = 0
        self.is_public = False
        self.is_deleted = False
        self.share_time = None
        self.hot_index = None # type: int|None
        self.update(kw)


def fix_note_public():
    db = dbutil.get_table("note_index")
    public_db = dbutil.get_table("note_public")
    for item in db.iter(limit = -1):
        note = NoteIndex(**item)
        note_id = note.id
        if note.is_deleted:
            continue
        if note.is_public:
            log_info("Fix public index:{}", note.id)
            if note.share_time is None:
                note.share_time = note.ctime
            if note.hot_index is None:
                note.hot_index = 1
            public_db.put_by_id(note_id, note)
