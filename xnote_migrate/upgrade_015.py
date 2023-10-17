# encoding=utf-8
import xtables
import xutils
import xauth
import logging

from . import base
from xutils import Storage
from xutils import dbutil
from xutils.db.dbutil_helper import new_from_dict
from handlers.message.dao import MsgIndex

def do_upgrade():
    # since 2.9.5
    base.execute_upgrade("20230826_msg_index", migrate_msg_index)

class MsgInfoV1(Storage):

    def __init__(self):
        self._id = ""
        self.tag = ""
        self.user = ""
        self.ctime = ""  # 展示创建时间
        self.ctime0 = "" # 实际创建时间

    @staticmethod
    def from_dict(dict_value):
        return new_from_dict(MsgInfoV1, dict_value)

def fix_datetime(datetime_str=""):
    if datetime_str == "":
        return ""
    
    default_value = "1970-01-01 00:00:00"
    
    if len(datetime_str) != len(default_value):
        logging.error("invalid datetime: %s", datetime_str)
        return default_value
    
    return datetime_str

def migrate_msg_index():
    """迁移随手记索引"""
    old_db = dbutil.get_table("message")
    old_db_backup = dbutil.get_table("msg_backup")
    new_db = xtables.get_table_by_name("msg_index")
    for item in old_db.iter(limit=-1):
        msg_info = MsgInfoV1.from_dict(item)
        msg_index = MsgIndex()
        kv_id = msg_info._id

        try:
            msg_index.id = int(kv_id)
        except:
            logging.info("无效的随手记ID: %s", msg_info)
            continue

        msg_index.tag = msg_info.tag
        if msg_index.tag in ("", None):
            msg_index.tag = "done"
        msg_index.ctime = fix_datetime(msg_info.ctime)
        msg_index.ctime_sys = fix_datetime(msg_info.ctime0)
        if msg_index.ctime_sys == "":
            msg_index.ctime_sys = msg_index.ctime
        msg_index.date = xutils.format_date(msg_info.ctime)
        msg_index.user_id = xauth.UserDao.get_id_by_name(msg_info.user)
        msg_index.user_name = msg_info.user
        old = new_db.select_first(where=dict(id=msg_index.id))
        if old != None:
            new_db.update(**msg_index, where=dict(id=msg_index.id))
        else:
            new_db.insert(**msg_index)
        
        if kv_id.startswith("0"):
            # 先备份再删除
            old_kv_key = msg_info._key
            new_kv_id = str(msg_index.id)
            old_db.update_by_id(new_kv_id, msg_info)
            old_db_backup.update_by_id(kv_id, msg_info)
            old_db.delete_by_key(old_kv_key)
            logging.info("迁移0前缀随手记, kv_id=%s", kv_id)
        
        logging.info("迁移随手记: %s", msg_index)
