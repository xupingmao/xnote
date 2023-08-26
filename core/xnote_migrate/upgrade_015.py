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
    base.execute_upgrade("20230826", migrate_msg_index)

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

def migrate_msg_index():
    """迁移随手记索引"""
    old_db = dbutil.get_table("message")
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
        msg_index.ctime = msg_info.ctime
        msg_index.ctime_sys = msg_info.ctime0
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
            old_db.update_by_id(str(msg_index.id), msg_info)
            logging.info("迁移0前缀随手记, kv_id=%s", kv_id)
        
        logging.info("迁移随手记: %s", msg_index)
