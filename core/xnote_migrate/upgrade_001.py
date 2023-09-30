# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/31 22:53:27
# @modified 2022/01/08 11:10:54
# @filename upgrade_001.py

"""user_note_log日志重建"""

from xutils import dbutil
from .base import log_info
from handlers.note import dao_log
from . import base

dbutil.register_table("note_migrate_log", "笔记迁移日志")

def do_upgrade():
    """升级入口"""
    old_key = "note_visit_log"
    new_key = "20211231_not_visit_log"
    base.move_upgrade_key(old_key=old_key, new_key=new_key)
    base.execute_upgrade(new_key, rebuild_visit_log)

#### 重建访问日志
def rebuild_visit_log():
    db = dbutil.get_table("note_index")
    for note in db.iter(limit = -1):
        note_id = str(note.id)
        if note.creator is None:
            log_info("invalid note:%r", note.id)
            continue
        if note.is_deleted:
            dao_log.delete_visit_log(note.creator, note_id)
            continue
        increment = note.visited_cnt or 1
        dao_log._update_log(note.creator, note, increment)
