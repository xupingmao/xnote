# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/18
# @modified 2020/01/18 21:29:54

"""时光轴视图"""
import re
import xauth
import xutils
import xtables
import xtemplate
from xutils import Storage, dateutil, textutil
from xtemplate import T

NOTE_DAO = xutils.DAO("note")


def build_date_result(rows, orderby):
    result = dict()
    for row in rows:
        if orderby == "mtime":
            date_time = row.mtime
        else:
            date_time = row.ctime

        date = re.match(r"\d+\-\d+\-\d+", date_time).group(0)
        # 优化返回数据大小
        row.content = ""
        if date not in result:
            result[date] = []
        if row.type == "group":
            row.url = "/note/timeline?type=default&parent_id=%s" % row.id
        else:
            row.url = "/note/%s?source=timeline" % row.id
        result[date].append(row)

    for key in result:
        items = result[key]
        items.sort(key = lambda x: x[orderby], reverse = True)
    return result

class TimelineAjaxHandler:

    def GET(self):
        offset     = xutils.get_argument("offset", 0, type=int)
        limit      = xutils.get_argument("limit", 20, type=int)
        type       = xutils.get_argument("type", "root")
        parent_id  = xutils.get_argument("parent_id", None, type=str)
        search_key = xutils.get_argument("key", None, type=str)
        user_name  = xauth.current_name()

        if type == "public":
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
        elif type == "root":
            rows = NOTE_DAO.list_group(user_name)
            orderby = "mtime"
        else:
            if type == "root":
                parent_id = 0
                # TODO 合并待办任务

            words = None
            if search_key != None and search_key != "":
                # TODO 公共笔记的搜索
                search_key = xutils.unquote(search_key)
                parent_id  = None
                words      = textutil.split_words(search_key)

            def list_func(key, value):
                if value.is_deleted:
                    return False
                if value.name is None:
                    return False
                if parent_id != None and str(value.parent_id) != str(parent_id):
                    return False
                if words != None and not textutil.contains_all(value.name, words):
                    return False
                return True
            rows = NOTE_DAO.list_by_func(user_name, list_func, offset, limit)

        orderby = "ctime"
        if type in ("mtime", "group", "root"):
            orderby = "mtime"

        return build_date_result(rows, orderby)

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

    default_type = "root"

    def GET(self):
        type        = xutils.get_argument("type", self.default_type)
        parent_id   = xutils.get_argument("parent_id")
        key         = xutils.get_argument("key", "")
        title       = T("最新笔记")
        show_create = True

        if type == "public":
            title = T("公共笔记")
            show_create = False
        else:
            xauth.check_login()

        if type == "gallery":
            title = T("相册")

        file = None
        if parent_id != None:
            file = NOTE_DAO.get_by_id(parent_id)
            title = file.name

        return xtemplate.render("note/tools/timeline.html", 
            title = title,
            type  = type,
            file  = file,
            key   = key,
            show_create = show_create,
            search_action = "/note/timeline",
            search_placeholder = "搜索笔记",
            show_aside = False)

class PublicTimelineHandler(TimelineHandler):
    """公共笔记的时光轴视图"""
    default_type = "public"


xurls = (
    r"/note/timeline", TimelineHandler,
    r"/note/public",   PublicTimelineHandler,
    r"/note/tools/timeline", TimelineHandler,
    r"/note/timeline/month", DateTimeline,
    r"/note/api/timeline", TimelineAjaxHandler,
)

