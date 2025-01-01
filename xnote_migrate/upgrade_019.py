# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-06-22 19:11:13
@LastEditors  : xupingmao
@LastEditTime : 2024-08-31 23:02:30
@FilePath     : /xnote/xnote_migrate/upgrade_019.py
@Description  : 描述
"""
import logging
import xutils

from xnote.core import xtables, xauth
from xnote_migrate import base
from xutils import dbutil, dateutil
from xutils.db.dbutil_helper import new_from_dict
from handlers.note.dao import NoteDO, create_note, NoteIndexDao
from xnote.service.search_service import SearchHistoryDO, SearchHistoryService, SearchHistoryType

def do_upgrade():
    # since v2.9.7
    handler = MigrateHandler()
    base.execute_upgrade("20240623_fix_note", handler.fix_invalid_note_id)
    base.execute_upgrade("20240623_note_history_index", handler.migrate_note_history_index)
    base.execute_upgrade("20240928_rebuild_msg", handler.rebuild_msg)
    base.execute_upgrade("20241026_migrate_search_history", handler.migrate_search_history)
    base.execute_upgrade("20241229_msg_idx_change_time", handler.rebuild_msg_idx_change_time)
    
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

class KvSearchHistory(xutils.Storage):
    def __init__(self) -> None:
        self.user = ""
        self.key = ""
        self.category = "default"
        self.cost_time = 0.0
        self.ctime = dateutil.format_datetime()
    
    @staticmethod
    def from_dict(dict_value):
        return new_from_dict(KvSearchHistory, dict_value)

class MsgIndex(xutils.Storage):
    def __init__(self, **kw):
        self.id = 0
        self.tag = ""
        self.user_id = 0
        self.user_name = ""
        self.ctime_sys = dateutil.format_datetime() # 实际创建时间
        self.ctime = dateutil.format_datetime() # 展示创建时间
        self.mtime = dateutil.format_datetime() # 修改时间
        self.date = xtables.DEFAULT_DATE
        self.sort_value = "" # 排序字段, 对于log/task,存储创建时间,对于done,存储完成时间
        self.change_time = xtables.DEFAULT_DATETIME
        self.update(kw)

    @classmethod
    def from_dict(cls, dict_value):
        result = MsgIndex()
        result.update(dict_value)
        return result
    
    def get_change_time(self):
        if not dateutil.is_empty_datetime(self.change_time):
            return self.change_time
        if self.sort_value == "":
            return self.mtime
        try:
            return str(dateutil.to_py_datetime(self.sort_value))
        except:
            return self.mtime
        
    def get_full_key(self):
        return f"msg_v2:{self.user_id}:{self.id}"

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

    def rebuild_msg(self):
        message_db = dbutil.get_table("message")
        new_msg_db = dbutil.get_table("msg_v2")
                
        for item in message_db.iter(limit=-1):
            user_id = item.get("user_id", 0)
            user_name = item.get("user", "")
            if user_id == 0:
                user_id = xauth.UserDao.get_id_by_name(user_name)
            msg_id = item.get("_id", "")
            if msg_id == "":
                raise Exception("msg_id is empty")
            item["user_id"] = user_id
            item["id"] = new_msg_db._build_key(str(user_id), msg_id)
            new_msg_db.put_by_id(msg_id, item)
    
    def upsert_search_history(self, item: KvSearchHistory, search_type: str):
        user_id = xauth.UserDao.get_id_by_name(item.user)

        new_item = SearchHistoryDO()
        new_item.ctime = item.ctime
        new_item.cost_time_ms = int(item.cost_time)
        new_item.user_id = user_id
        new_item.search_type = search_type
        new_item.search_key = item.key

        if user_id == 0:
            logging.info("user_id=0, skip search_history")
            return

        check_old = SearchHistoryService.find_one(user_id=user_id, 
                                                  search_type=search_type, search_key=item.key, ctime=new_item.ctime)
        if check_old is None:
            SearchHistoryService.create(new_item)

    def migrate_search_history(self):
        search_history_db = dbutil.get_table("search_history")
        msg_search_history_db = dbutil.get_table("msg_search_history")

        for raw_item in search_history_db.iter(limit=-1):
            item = KvSearchHistory.from_dict(raw_item)
            self.upsert_search_history(item, SearchHistoryType.default)
        
        for raw_item in msg_search_history_db.iter(limit=-1):
            item = KvSearchHistory.from_dict(raw_item)
            self.upsert_search_history(item, SearchHistoryType.msg)


    def rebuild_msg_idx_change_time(self):
        msg_index_db = xtables.get_table_by_name("msg_index")
        msg_full_db = dbutil.get_table("msg_v2")
        for batch in msg_index_db.iter_batch():
            for row in batch:
                msg_index = MsgIndex.from_dict(row)
                new_change_time = msg_index.get_change_time()
                if new_change_time != msg_index.change_time:
                    full_key = msg_index.get_full_key()
                    full_info = msg_full_db.get_by_key(full_key)
                    if full_info != None:
                        full_info.pop("sort_value", None)
                        full_info["change_time"] = new_change_time
                        msg_full_db.update(full_info)
                    msg_index_db.update(where=dict(id=msg_index.id), change_time = new_change_time)

                        