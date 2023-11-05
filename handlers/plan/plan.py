# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-02-12 00:00:00
@LastEditors  : xupingmao
@LastEditTime : 2023-11-05 22:54:32
@FilePath     : /xnote/handlers/plan/plan.py
@Description  : 计划管理
"""
from xnote.core import xauth, xtemplate
import xutils
import datetime
from xutils import Storage
from handlers.plan.dao import MonthPlanDao
from handlers.note import dao as note_dao
from xutils import functions, dateutil

class MonthPlanHandler:

    @xauth.login_required()
    def GET(self):
        kw = Storage()
        user_info = xauth.current_user()
        assert user_info != None
        
        date = xutils.get_argument_str("date", "now")
        date = date.replace("/", "-")
        record = MonthPlanDao.get_or_create(user_info, date)

        if len(record.note_ids) > 0:
            note_ids = list(filter(lambda x:x!="", record.note_ids))
            record.notes = note_dao.batch_query_list(note_ids)
            record.notes.sort(key = lambda x:x.name)

        year, month = record.month.split("-")
        int_year = int(year)
        int_month = int(month)
        user_id = user_info.id

        kw.record = record
        kw.year = int_year
        kw.month = int_month

        next_year = int_year
        next_month = int_month + 1
        if next_month == 13:
            next_year += 1
            next_month = 1

        date_start = datetime.datetime(year=int_year, month=int_month, day=1)
        date_end = datetime.datetime(year=next_year, month=next_month, day=1)
        kw.created_notes = note_dao.NoteIndexDao.list(creator_id=user_id, 
                                                      date_start=dateutil.format_datetime(date_start), 
                                                      date_end=dateutil.format_datetime(date_end))
        return xtemplate.render("plan/page/month_plan.html", **kw)


class MonthPlanAddAjaxHandler:
    @xauth.login_required()
    def POST(self):
        plan_id = xutils.get_argument_str("id", "")
        note_ids_str = xutils.get_argument_str("note_ids", "")
        note_ids = note_ids_str.split(",")
        if plan_id == "":
            return dict(code="400", message="参数id不能为空")

        user_id = xauth.current_user_id()
        record = MonthPlanDao.get_by_id(user_id, plan_id)
        if record != None:
            assert isinstance(note_ids, list)
            for id in note_ids:
                if id not in record.note_ids:
                    record.note_ids.append(id)
            record.save()
            return dict(code="success")
        else:
            return dict(code="500", message="计划不存在")

class MonthPlanRemoveAjaxHandler:
    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument_str("id", "")
        note_id = xutils.get_argument_str("note_id", "")
        if id == "":
            return dict(code="400", message="参数id不能为空")
        if note_id == "":
            return dict(code="400", message="参数note_id不能为空")

        user_id = xauth.current_user_id()
        record = MonthPlanDao.get_by_id(user_id, id)
        if record != None:
            functions.listremove(record.note_ids, note_id)
            record.save()
            return dict(code="success")
        else:
            return dict(code="500", message="计划不存在")

xurls = (
    r"/plan/month", MonthPlanHandler,
    r"/plan/month/add", MonthPlanAddAjaxHandler,
    r"/plan/month/remove", MonthPlanRemoveAjaxHandler,
)