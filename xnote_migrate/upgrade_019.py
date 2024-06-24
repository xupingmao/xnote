# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-06-22 19:11:13
@LastEditors  : xupingmao
@LastEditTime : 2024-06-25 00:33:37
@FilePath     : /xnote/xnote_migrate/upgrade_019.py
@Description  : 描述
"""
import logging
import xutils

from xnote.core import xtables, xauth
from . import base
from xutils import dbutil, dateutil
from xutils.db.dbutil_helper import new_from_dict
from handlers.note.dao import NoteDO, create_note, NoteIndexDao

def do_upgrade():
    # since v2.9.7
    handler = MigrateHandler()
    base.execute_upgrade("20240623_fix_note", handler.fix_invalid_note_id)
    base.execute_upgrade("20240623_note_history_index", handler.migrate_note_history_index)
    
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


class KvNoteIndexDO(xutils.Storage):
    def __init__(self):
        self.id = "" # id是str
        self.name = ""
        self.path = ""
        self.creator = ""
        self.ctime = dateutil.format_datetime()
        self.mtime = dateutil.format_datetime()
        self.atime = dateutil.format_datetime()
        self.share_time = self.ctime
        self.type = "md"
        self.category = "" # 废弃
        self.size = 0
        self.children_count = 0
        self.parent_id = "0" # 默认挂在根目录下
        self.content = ""
        self.data = ""
        self.is_deleted = 0 # 0-正常， 1-删除
        self.is_public = 0  # 0-不公开, 1-公开
        self.token = ""
        self.priority = 0 
        self.visited_cnt = 0
        self.orderby = ""
        # 热门指数
        self.hot_index = 0
        # 版本
        self.version = 0
        self.tags = []

    @staticmethod
    def from_dict(dict_value):
        return new_from_dict(KvNoteIndexDO, dict_value)

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


    def fix_invalid_note_id(self):
        note_full_db = dbutil.get_table("note_full")
        for item in note_full_db.iter(limit=-1):
            kv_item = KvNoteIndexDO.from_dict(item)
            if base.is_valid_int(kv_item.id):
                continue
            if kv_item.is_deleted == 1:
                logging.info("note is deleted, note_id:%s, note_name:%s", kv_item.id, kv_item.name)
                continue

            if kv_item.tags is None:
                kv_item.tags = []

            logging.info("find invalid note_id:%s, note_name:%s", kv_item.id, kv_item.name)

            creator_id = xauth.UserDao.get_id_by_name(kv_item.creator)

            new_note = NoteDO()
            new_note.type = kv_item.type
            new_note.name = kv_item.name
            new_note.creator = kv_item.creator
            new_note.creator_id = creator_id
            new_note.parent_id = int(kv_item.parent_id)
            new_note.content = kv_item.content
            new_note.data = kv_item.data
            new_note.hot_index = kv_item.hot_index
            new_note.is_public = kv_item.is_public
            new_note.tags = kv_item.tags
            new_note.visit_cnt = kv_item.visited_cnt
            new_note.priority = kv_item.priority
            new_note.level = kv_item.priority

            date_str = dateutil.format_date(kv_item.ctime)

            old_note = NoteIndexDao.get_by_name(creator_id=creator_id, name=kv_item.name)
            if old_note != None:
                logging.info("note with same name found, creator_id:%s, name:%s", creator_id, kv_item.name)
                continue

            new_note_id = create_note(new_note, date_str=date_str)
            # 标记为删除
            kv_item.is_deleted = 1
            note_full_db.update(kv_item)
            logging.info("fix note_id success, old_id:%s, new_id:%s", kv_item.id, new_note_id)