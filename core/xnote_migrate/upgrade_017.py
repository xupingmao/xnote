import xtables
import xutils
import xauth
import logging
import handlers.note.dao as note_dao

from . import base
from xutils import Storage
from xutils import dbutil, dateutil
from xutils.db.dbutil_helper import new_from_dict

def do_upgrade():
    handler = MigrateHandler()
    base.execute_upgrade("20230916_note_index", handler.migrate_note_index)
    base.execute_upgrade("20230917_note_share", handler.migrate_note_share)



class KvNoteIndexDO(Storage):
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

class KvNoteShareDO(Storage):
    def __init__(self, **kw):
        self.from_user = kw.get("from_user", "")
        self.to_user = kw.get("to_user", "")
        self.note_id = kw.get("note_id", "")

class NoteIndexDO(Storage):
    def __init__(self):
        self.id = 0
        self.name = ""
        self.creator = ""
        self.creator_id = 0
        self.type = ""
        self.ctime = dateutil.format_datetime()
        self.mtime = dateutil.format_datetime()
        self.parent_id = 0
        self.size = 0
        self.version = 0
        self.is_deleted = 0
        self.is_public = 0
        self.level = 0
        self.children_count = 0
        self.tag_str = ""

    @staticmethod
    def from_dict(dict_value):
        return new_from_dict(NoteIndexDO, dict_value)


class ShareInfoDO(Storage):
    def __init__(self):
        self.ctime = dateutil.format_datetime()
        self.share_type = ""
        self.target_id = 0
        self.from_id = 0
        self.to_id = 0

class MigrateHandler:

    share_db = xtables.get_table_by_name("share_info")
    kv_note_share = dbutil.get_table("note_share")
    user_dao = xauth.UserDao

    def migrate_note_index(self):
        """迁移笔记索引"""
        old_db = dbutil.get_table("note_index")
        new_db = xtables.get_table_by_name("note_index")
        note_full_db = dbutil.get_table("note_full")
        

        for item in old_db.iter(limit=-1):
            old_index = KvNoteIndexDO.from_dict(item)
            new_index = NoteIndexDO()

            try:
                note_id = int(old_index.id)
            except:
                base.add_failed_log("note_index", old_index, reason="note_id无法转换成数字")
                continue

            creator = old_index.creator
            creator_id = xauth.UserDao.get_id_by_name(creator)

            if old_index.tags == None:
                old_index.tags = []

            new_index.id = note_id
            new_index.name = old_index.name
            new_index.creator = old_index.creator
            new_index.creator_id = creator_id
            new_index.name = old_index.name
            new_index.parent_id = int(old_index.parent_id)
            new_index.ctime = old_index.ctime
            new_index.mtime = old_index.mtime
            new_index.type = old_index.type or "md"
            new_index.size = old_index.size or 0
            new_index.level = old_index.priority or 0
            new_index.children_count = old_index.children_count or 0
            new_index.is_deleted = old_index.is_deleted
            new_index.is_public = old_index.is_public
            new_index.tag_str = " ".join(old_index.tags)
            if old_index.archived:
                new_index.level = -1

            if old_index.is_public:
                self.upsert_public_note(new_index, old_index.share_time)

            old_note_id = str(old_index.id)
            if str(note_id) != old_note_id:
                full_do = note_full_db.get_by_id(old_note_id)
                if full_do != None:
                    note_full_db.update_by_id(str(note_id), full_do)
                    note_full_db.delete_by_id(old_note_id)

            old = new_db.select_first(where=dict(id=note_id))
            if old != None:
                new_db.update(**new_index, where=dict(id=new_index.id))
            else:
                new_db.insert(**new_index)
            
            logging.info("迁移笔记索引: %s", new_index)

    def upsert_public_note(self, index: NoteIndexDO, share_time:str):
        note_id = index.id
        share_info = self.share_db.select_first(where=dict(target_id=note_id))
        if share_info == None:
            new_share = ShareInfoDO()
            new_share.ctime = share_time
            new_share.share_type = "note_public"
            new_share.target_id = index.id
            new_share.from_id = index.creator_id
            self.share_db.insert(**new_share)
            logging.info("迁移笔记分享: %s", new_share)


    def migrate_note_share(self):
        for item in self.kv_note_share.iter(limit=-1):
            kv_share = KvNoteShareDO(**item)
            note_id = int(kv_share.note_id)
            from_id = self.user_dao.get_id_by_name(kv_share.from_user)
            to_id = self.user_dao.get_id_by_name(kv_share.to_user)
            share_type = note_dao.ShareTypeEnum.note_to_user.value
            where = dict(target_id=note_id, from_id=from_id, to_id=to_id, 
                         share_type=share_type)
            share_info = self.share_db.select_first(where=where)
            if share_info == None:
                new_share = ShareInfoDO()
                new_share.ctime = dateutil.format_datetime()
                new_share.share_type = share_type
                new_share.target_id = note_id
                new_share.from_id = from_id
                new_share.to_id = to_id
                self.share_db.insert(**new_share)