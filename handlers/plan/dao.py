# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-02-12 00:00:00
@LastEditors  : xupingmao
@LastEditTime : 2023-01-22 00:07:43
@FilePath     : /xnote/handlers/note/note_helper.py
@Description  : 计划管理
"""
import time
from xutils import dbutil
db = dbutil.get_table("month_plan")

class MonthPlanRecord:

    def __init__(self) -> None:
        self.user = ""
        self.month = ""
        self.notes = []
        self.note_ids = []

    @staticmethod
    def from_dict(dict_value):
        result = MonthPlanRecord()
        result.__dict__.update(dict_value)
        return result
    
    def to_dict(self):
        return self.__dict__
    
    def save(self):
        MonthPlanDao.update(self)

class MonthPlanDao:

    @staticmethod
    def get_or_create(user_name = "", month = "2020/03"):
        if month == "now":
            month = time.strftime("%Y/%m")
        record = db.first_by_index("user_month", where = dict(user=user_name, month = month))
        if record == None:
            record = MonthPlanRecord()
            record.user = user_name
            record.month = month
            id = db.insert(record.to_dict())
            record = db.get_by_id(id)
        
        assert isinstance(record, dict)
        return MonthPlanRecord.from_dict(record)

    @staticmethod
    def get_by_id(user_name = "", id = ""):
        record = db.get_by_id(id)
        if record == None:
            return None
        if record.user != user_name:
            return None
        return MonthPlanRecord.from_dict(record)
    
    @staticmethod
    def get_by_month(user_name = "", month = "2020/03"):
        record = db.first_by_index("user_month", where = dict(user=user_name, month = month))
        if record == None:
            return None
        return MonthPlanRecord.from_dict(record)
    
    @staticmethod
    def update(record: MonthPlanRecord):
        db.update(record.to_dict())
