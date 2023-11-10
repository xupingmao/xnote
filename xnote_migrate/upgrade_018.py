# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-11-05 19:11:13
@LastEditors  : xupingmao
@LastEditTime : 2023-11-10 23:43:19
@FilePath     : /xnote/xnote_migrate/upgrade_018.py
@Description  : 描述
"""

from xnote.core import xauth
from xutils import dbutil, Storage
from . import base
import logging

def do_upgrade():
    # since v2.9.6
    handler = MigrateHandler()
    base.execute_upgrade("20231105_month_plan", handler.migrate_month_plan)

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