# encoding=utf-8
import xtables
import xutils
import xauth
import logging

from . import base
from xutils import Storage
from xutils import dbutil, dateutil
from xutils.db.dbutil_helper import new_from_dict

def do_upgrade():
    # since 2.9.5
    base.execute_upgrade("20230910_comment_index", migrate_comment_index)


class CommentDO(Storage):
    def __init__(self):
        self._id = ""
        self.user = ""
        self.user_id = 0
        self.note_id = ""
        self.type = ""
        self.content = ""
        self.ctime = dateutil.format_datetime()

    @staticmethod
    def from_dict(dict_value):
        return new_from_dict(CommentDO, dict_value)


class CommentIndexDO(Storage):
    def __init__(self):
        self.ctime = dateutil.format_datetime()
        self.mtime = dateutil.format_datetime()
        self.type = ""
        self.user_id = 0
        self.target_id = 0

def migrate_comment_index():
    """迁移随手记索引"""
    old_db = dbutil.get_table("comment")
    new_db = xtables.get_table_by_name("comment_index")

    for item in old_db.iter(limit=-1):
        comment_info = CommentDO.from_dict(item)
        comment_index = CommentIndexDO()

        idx_id = int(comment_info._id)
        user_id = comment_info.user_id
        if user_id == 0:
            user_id = xauth.UserDao.get_id_by_name(comment_info.user)

        comment_index.id = idx_id
        comment_index.ctime = comment_info.ctime
        comment_index.mtime = comment_info.ctime
        comment_index.type = comment_info.type or ""
        comment_index.user_id = user_id

        try:
            comment_index.target_id = int(comment_info.note_id)
        except:
            base.add_failed_log("comment", comment_info, reason="note_id无法转换成数字")
            continue

        old = new_db.select_first(where=dict(id=idx_id))
        if old != None:
            new_db.update(**comment_index, where=dict(id=comment_index.id))
        else:
            new_db.insert(**comment_index)
        
        old_idx_id = comment_info._id
        new_idx_id = str(idx_id)
        if new_idx_id != old_idx_id:
            old_db.update_by_id(new_idx_id, comment_info)
            old_db.delete_by_id(old_idx_id)
        
        logging.info("迁移评论: %s", comment_index)
