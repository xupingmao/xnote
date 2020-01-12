# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/18
# @modified 2020/01/12 13:21:21

"""时光轴视图"""
import re
import xauth
import xutils
import xtables
import xtemplate
from xtemplate import T

NOTE_DAO = xutils.DAO("note")

class TimelineAjaxHandler:

    def GET(self):
        offset = xutils.get_argument("offset", 0, type=int)
        limit  = xutils.get_argument("limit", 20, type=int)
        type   = xutils.get_argument("type", "default")
        user_name  = xauth.current_name()

        if type == "mtime":
            rows = NOTE_DAO.list_recent_edit(user_name, offset, limit)
        elif type == "public":
            rows = NOTE_DAO.list_public(offset, limit)
        elif type == "sticky":
            rows = NOTE_DAO.list_sticky(user_name, offset, limit)
        elif type == "removed":
            rows = NOTE_DAO.list_removed(user_name, offset, limit)
        elif type in ("md", "group", "gallery", "document", "list", "table", "csv"):
            rows = NOTE_DAO.list_by_type(user_name, type, offset, limit)
        elif type == "archived":
            rows = NOTE_DAO.list_archived(user_name, offset, limit)
        elif type == "all":
            rows = NOTE_DAO.list_recent_created(user_name, offset, limit)
        else:
            rows = NOTE_DAO.list_recent_created(user_name, offset, limit, skip_archived = True)

        orderby = "ctime"
        result = dict()
        for row in rows:
            if type == "mtime":
                date_time = row.mtime
                orderby = "mtime"
            else:
                date_time = row.ctime
                orderby = "ctime"

            date = re.match(r"\d+\-\d+\-\d+", date_time).group(0)
            # 优化数据大小
            row.content = ""
            if date not in result:
                result[date] = []
            result[date].append(row)

        for key in result:
            items = result[key]
            items.sort(key = lambda x: x[orderby], reverse = True)
        return result

class DateTimeline:
    @xauth.login_required()
    def GET(self):
        year  = xutils.get_argument("year")
        month = xutils.get_argument("month")
        if len(month) == 1:
            month = "0" + month
        user_name  = xauth.current_name()
        rows = NOTE_DAO.list_by_date("ctime", user_name, "%s-%s" % (year, month))
        result = dict()
        for row in rows:
            date = re.match(r"\d+\-\d+", row.ctime).group(0)
            # 优化数据大小
            row.content = ""
            if date not in result:
                result[date] = []
            result[date].append(row)
        return result

class TimelineHandler:

    def GET(self):
        type  = xutils.get_argument("type")
        title = T("最新笔记")
        if type == "public":
            title = T("公共笔记")
        else:
            xauth.check_login()

        if type == "gallery":
            title = T("相册")

        return xtemplate.render("note/tools/timeline.html", 
            title = title,
            show_aside = False)

xurls = (
    r"/note/timeline", TimelineHandler,
    r"/note/tools/timeline", TimelineHandler,
    r"/note/timeline/month", DateTimeline,
    r"/note/api/timeline", TimelineAjaxHandler,
)

