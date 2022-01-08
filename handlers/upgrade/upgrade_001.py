# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/31 22:53:27
# @modified 2022/01/08 11:10:54
# @filename upgrade_001.py

"""user_note_log日志重建"""

import xmanager
import xutils
from xutils import dbutil
from handlers.upgrade.upgrade_main import log_info

dbutil.register_table("note_migrate_log", "笔记迁移日志")
NOTE_DAO = xutils.DAO("note")

def get_note_migrate_log_table():
    return dbutil.get_hash_table("note_migrate_log")

def is_migrate_done(op_flag):
    db = get_note_migrate_log_table()
    return db.get(op_flag) == "1"

def mark_migrate_done(op_flag):
    db = get_note_migrate_log_table()
    db.put(op_flag, "1")

#### 重建访问日志
def rebuild_visit_log():
    if is_migrate_done("note_visit_log"):
        log_info("note_visit_log migrate done")
        return

    db = dbutil.get_table("note_index")
    for note in db.iter(limit = -1):
        note_id = str(note.id)
        if note.creator is None:
            log_info("invalid note:%r", note.id)
            continue
        if note.is_deleted:
            NOTE_DAO.delete_visit_log(note.creator, note_id)
            continue
        increment = note.visited_cnt or 1
        NOTE_DAO._update_log(note.creator, note, increment)

    mark_migrate_done("note_visit_log")

def do_upgrade():
    """升级入口"""
    rebuild_visit_log()
