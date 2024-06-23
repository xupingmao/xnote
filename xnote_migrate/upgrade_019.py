# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-06-22 19:11:13
@LastEditors  : xupingmao
@LastEditTime : 2024-06-23 10:22:40
@FilePath     : /xnote/xnote_migrate/upgrade_019.py
@Description  : 描述
"""
import logging
import xutils

from xnote.core import xtables
from . import base
from xutils import dbutil

def do_upgrade():
    # since v2.9.7
    handler = MigrateHandler()
    base.execute_upgrade_async("20240623_note_history_index", handler.migrate_note_history_index)
    
class NoteHistoryKvIndexDO(xutils.Storage):
    def __init__(self, **kw):
        self.note_id = 0
        self.name = ""
        self.version = 0
        self.mtime = xtables.DEFAULT_DATETIME
        self.update(kw)

class NoteHistoryNewIndexDO(xutils.Storage):
    def __init__(self, **kw):
        self.note_id = 0
        self.name = ""
        self.version = 0
        self.mtime = xtables.DEFAULT_DATETIME
        self.creator_id = 0
        self.update(kw)

class MigrateHandler:

    note_index_db = note_index_db = xtables.get_table_by_name("note_index")

    def get_note_index_by_id(self, note_id=0):
        if note_id <= 0:
            return None
        return self.note_index_db.select_first(where=dict(id=note_id))

    def migrate_note_history_index(self):
        old_db = dbutil.get_table("note_history_index")
        new_index_db = xtables.get_table_by_name("note_history_index")

        for item in old_db.iter(limit=-1):
            kv_index = NoteHistoryKvIndexDO(**item)
            note_id = kv_index.note_id
            version = kv_index.version
            
            new_index = NoteHistoryNewIndexDO()

            try:
                note_id = int(note_id)
                version = int(version)
                base.validate_datetime(kv_index.mtime)

                new_index.note_id = note_id
                new_index.name = str(kv_index.name)
                new_index.mtime = kv_index.mtime
                new_index.version = version
            except:
                logging.error("invalid note history index: %s", kv_index)
                continue

            note_index = self.get_note_index_by_id(note_id)

            if note_index != None:
                new_index.creator_id = note_index.creator_id
            
            check_index = new_index_db.select_first(where=dict(note_id=note_id, version=version))
            if check_index == None:
                logging.info("insert new index: %s", new_index)
                new_index_db.insert(**new_index)


