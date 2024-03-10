# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-11-05 19:11:13
@LastEditors  : xupingmao
@LastEditTime : 2024-03-10 15:21:20
@FilePath     : /xnote/xnote_migrate/upgrade_018.py
@Description  : 描述
"""

from xnote.core import xauth, xtables
from xutils import dbutil, Storage
from xutils.sqldb.utils import safe_str
from . import base
import logging
from xutils import dateutil
import xutils

def do_upgrade():
    # since v2.9.6
    handler = MigrateHandler()
    base.execute_upgrade("20231105_month_plan", handler.migrate_month_plan)
    base.execute_upgrade("20231223_msg_index", handler.migrate_msg_index)
    base.execute_upgrade("20240214_plugin_visit", handler.migrate_plugin_visit)
    base.execute_upgrade("20240214_user_op_log", handler.migrate_user_op_log)
    # base.execute_upgrade("20240308_msg_history", handler.migrate_msg_history)
    xutils.register_func("upgrade.20240308_msg_history",handler.migrate_msg_history)
    

class MonthPlanRecord(Storage):
    def __init__(self, **kw):
        self._id = ""
        self._key = ""
        self.user = ""
        self.user_id = 0
        self.month = ""
        self.notes = []
        self.note_ids = []
        self.create_notes = []
        self.update_notes = []
        self.update(kw)


class MsgIndexDO(Storage):
    def __init__(self, **kw):
        self.id = 0
        self.tag = ""
        self.user_id = 0
        self.user_name = ""
        self.ctime_sys = dateutil.format_datetime() # 实际创建时间
        self.ctime = dateutil.format_datetime() # 展示创建时间
        self.mtime = dateutil.format_datetime() # 修改时间
        self.date = "1970-01-01"
        self.sort_value = "" # 排序字段, 对于log/task,存储创建时间,对于done,存储完成时间
        self.update(kw)

class PluginVisitDO(Storage):
    
    def __init__(self, **kw):
        self.name = "test"
        self.url = "/test"
        self.args = "name=1&age=2"
        self.user = ""
        self.visit_cnt = 0
        self.time = dateutil.format_datetime()
        self.update(kw)
    
class PageVisitLogDO(Storage):
    
    def __init__(self, **kw):
        self.user_id = 0
        self.url = "/test"
        self.args = "name=1&age=2"
        self.visit_cnt = 0
        self.visit_time = dateutil.format_datetime()
        self.update(kw)
        
class UserOpLogV1(Storage):
    def __init__(self, **kw):
        self.ctime = dateutil.format_datetime()
        self.user_name = ""
        self.type = ""
        self.detail = ""
        self.ip = ""
        self.update(kw)

class UserOpLogV2(Storage):
    def __init__(self, **kw):
        self.ctime = dateutil.format_datetime()
        self.user_id = 0
        self.type = ""
        self.detail = ""
        self.ip = ""
        self.update(kw)

class MessageHistoryV1(Storage):
    def __init__(self, **kw):
        self.id = ""
        self.version = 0
        self.user_id = 0
        self.user = ""
        self.content = ""
        self.ctime = dateutil.format_datetime()
        self.mtime = dateutil.format_datetime()
        self.update(kw)

class MessageHistoryV2(Storage):
    def __init__(self, **kw):
        self.msg_id = 0
        self.msg_version = 0
        self.user_id = 0
        self.content = ""
        self.ctime = dateutil.format_datetime()
        self.update(kw)

class MigrateHandler:

    @classmethod
    def migrate_month_plan(cls):
        db = dbutil.get_table_v2("month_plan")
        for item in db.iter_by_kv():
            record = MonthPlanRecord(**item)
            if not record._id.isnumeric():
                # 老版本的数据放弃修复，重新插入会导致id重复
                logging.warning("ignore invalid key=%s", record._key)
                continue
            record.user_id = xauth.UserDao.get_id_by_name(record.user)
            record.month = record.month.replace("/", "-")
            db.update(record)

    @classmethod
    def migrate_msg_index(cls):
        db = xtables.get_table_by_name("msg_index")
        for item in db.iter():
            msg_index = MsgIndexDO(**item)
            if msg_index.sort_value in ("", xtables.DEFAULT_DATETIME):
                if msg_index.tag == "done":
                    msg_index.sort_value = msg_index.mtime
                else:
                    msg_index.sort_value = msg_index.ctime
                db.update(where=dict(id=msg_index.id), _skip_binlog=True, _skip_profile=True, sort_value = msg_index.sort_value)
    
    
    @classmethod
    def migrate_plugin_visit(cls):
        old_db = dbutil.get_table("plugin_visit")
        new_db = xtables.get_table_by_name("page_visit_log")
        for item0 in old_db.iter(limit=-1):
            item = PluginVisitDO(**item0)
            user_id = xauth.UserDao.get_id_by_name(item.user)
            exist = new_db.select_first(where=dict(user_id=user_id, url=item.url))
            if exist != None:
                continue
            else:
                new_record = PageVisitLogDO()
                new_record.user_id = user_id
                new_record.visit_time = item.time
                new_record.visit_cnt = item.visit_cnt
                new_record.url = safe_str(item.url)
                new_record.args = safe_str(item.args)
                new_db.insert(**new_record)
    
    
    @classmethod
    def migrate_user_op_log(cls):
        old_db = dbutil.get_table("user_op_log")
        new_db = xtables.get_table_by_name("user_op_log")
        for item0 in old_db.iter(limit=-1):
            item = UserOpLogV1(**item0)
            user_id = xauth.UserDao.get_id_by_name(item.user_name)
            if user_id == 0:
                logging.info("invalid user_op_log, %s", item0)
                continue
            exist = new_db.select_first(where=dict(user_id=user_id, ctime=item.ctime))
            if exist == None:
                new_record = UserOpLogV2()
                new_record.user_id = user_id
                new_record.ctime = item.ctime
                new_record.type = item.type
                new_record.detail = item.detail
                new_record.ip = item.ip
                new_db.insert(**new_record)
    
    
    @classmethod
    def migrate_msg_history(cls):
        db = dbutil.get_table_v2("msg_history")
        for item0 in db.iter_by_kv():
            item = MessageHistoryV1(**item0)
            if item.id == "":
                continue
            
            msg_id = int(db._get_id_from_key(item.id))
            version = item.get("version", 0)
            user_id = item.get("user_id", 0)
            
            assert msg_id > 0
            assert version >= 0
            if user_id == 0:
                user_id = xauth.UserDao.get_id_by_name(item.user)
            
            first = db.select_first(where=dict(msg_id=msg_id, msg_version=version))
            
            new_item = MessageHistoryV2()
            new_item.msg_id = msg_id
            new_item.msg_version = version
            new_item.user_id = user_id
            new_item.ctime = item.mtime
            new_item.content = item.content
            
            if first is None:
                db.insert(new_item)
