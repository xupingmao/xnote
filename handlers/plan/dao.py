# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-02-12 00:00:00
@LastEditors  : xupingmao
@LastEditTime : 2023-06-24 10:10:33
@FilePath     : /xnote/handlers/plan/dao.py
@Description  : 计划管理
"""
import time
from xnote.core import xauth
from xutils import dbutil, Storage

class MonthPlanRecord(Storage):

    def __init__(self, **kw):
        self.user = ""
        self.user_id = 0
        self.month = ""
        self.notes = []
        self.note_ids = []
        self.create_notes = []
        self.update_notes = []
        self.update(kw)
    
    def save(self):
        MonthPlanDao.update(self)

class MonthPlanDao:

    db = dbutil.get_table_v2("month_plan")

    @classmethod
    def get_or_create(cls, user_info: xauth.UserDO, month = "2020-03"):
        db = cls.db
        if month == "now":
            month = time.strftime("%Y-%m")
        user_id = user_info.id
        user_name = user_info.name

        record = db.select_first(where = dict(user_id=user_id, month = month))
        if record == None:
            record = MonthPlanRecord()
            record.user_id = user_id
            record.user = user_name
            record.month = month
            id = db.insert(record)
            record = db.get_by_id(id)
        
        assert isinstance(record, dict)
        return MonthPlanRecord(**record)

    @classmethod
    def get_by_id(cls, user_id = 0, id = ""):
        db = cls.db
        record = db.get_by_id(id)
        if record == None:
            return None
        if record.user_id != user_id:
            return None
        return MonthPlanRecord(**record)
    
    @classmethod
    def get_by_month(cls, user_id = 0, month = "2020-03"):
        db = cls.db
        record = db.select_first(where = dict(user_id=user_id, month = month))
        if record == None:
            return None
        return MonthPlanRecord(**record)
    
    @classmethod
    def update(cls, record: MonthPlanRecord):
        return cls.db.update(record)
