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
import xtemplate
import xauth
import xutils
from xutils import Storage
from handlers.plan.dao import MonthPlanDao
from handlers.note import dao as note_dao
from xutils import functions

class MonthPlanHandler:

    @xauth.login_required()
    def GET(self):
        kw = Storage()
        user_name = xauth.current_name()
        date = xutils.get_argument("date", "now")
        date = date.replace("-", "/")
        record = MonthPlanDao.get_or_create(user_name, date)

        if len(record.note_ids) > 0:
            note_ids = list(filter(lambda x:x!="", record.note_ids))
            record.notes = note_dao.batch_query_list(note_ids)
            record.notes.sort(key = lambda x:x.name)

        year, month = record._id.split("/")

        kw.record = record
        kw.year = int(year)
        kw.month = int(month)
        return xtemplate.render("plan/page/month_plan.html", **kw)


class MonthPlanAddAjaxHandler:
    @xauth.login_required()
    def POST(self):
        month = xutils.get_argument("month", "")
        note_ids_str = xutils.get_argument("note_ids", "")
        note_ids = note_ids_str.split(",")
        if month == "":
            return dict(code="400", message="参数month不能为空")

        user_name = xauth.current_name()
        record = MonthPlanDao.get_by_month(user_name, month)
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
        month = xutils.get_argument("month", "")
        note_id = xutils.get_argument("note_id", "")
        if month == "":
            return dict(code="400", message="参数month不能为空")

        user_name = xauth.current_name()
        record = MonthPlanDao.get_by_month(user_name, month)
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