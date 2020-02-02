# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/18
# @modified 2020/02/02 11:34:16

"""时光轴视图"""
import re
import xauth
import xutils
import xtables
import xtemplate
from xutils import Storage, dateutil, textutil
from xtemplate import T

NOTE_DAO = xutils.DAO("note")
MSG_DAO  = xutils.DAO("message")

class TaskGroup(Storage):
    def __init__(self):
        super(TaskGroup, self).__init__()
        user_name = xauth.current_name()
        self.type = 'system'
        self.name = "待办任务"
        self.icon = "fa-calendar-check-o"
        self.ctime = dateutil.format_time()
        self.mtime = dateutil.format_time()
        self.url  = "/message?tag=task"
        self.priority = 1
        self.size = MSG_DAO.get_message_stat(user_name).task_count

def search_group(user_name, words):
    rows = NOTE_DAO.list_group(user_name)
    result = []
    for row in rows:
        if textutil.contains_all(row.name, words):
            result.append(row)
    return result

def build_date_result(rows, type, orderby):
    result = dict()
    for row in rows:
        if orderby == "mtime":
            date_time = row.mtime
        else:
            date_time = row.ctime

        if type not in ("sticky", "public") and row.priority != None and row.priority > 0:
            title = '置顶'
        else:
            title = re.match(r"\d+\-\d+\-\d+", date_time).group(0)
        # 优化返回数据大小
        row.content = ""
        if title not in result:
            result[title] = []
        result[title].append(row)

    for key in result:
        items = result[key]
        items.sort(key = lambda x: x[orderby], reverse = True)
    return dict(code = 'success', data = result)

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
            rows.insert(0, TaskGroup())
            orderby = "mtime"
        else:
            # 主要是搜索
            words = None
            if search_key != None and search_key != "":
                # TODO 公共笔记的搜索
                search_key = xutils.unquote(search_key)
                search_key_lower = search_key.lower()
                parent_id  = None
                words      = textutil.split_words(search_key_lower)
                # groups = search_group(user_name, words)

            def list_func(key, value):
                if value.is_deleted:
                    return False
                if value.name is None:
                    return False
                if parent_id != None and str(value.parent_id) != str(parent_id):
                    return False
                if words != None and not textutil.contains_all(value.name.lower(), words):
                    return False
                return True
            # TODO 搜索公开内容
            rows = NOTE_DAO.list_by_func(user_name, list_func, offset, limit)

        orderby = "ctime"
        if type in ("mtime", "group", "root"):
            orderby = "mtime"

        return build_date_result(rows, type, orderby)

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

        return xtemplate.render("note/timeline.html", 
            title = title,
            type  = type,
            file  = file,
            key   = key,
            show_create = show_create,
            search_action = "/note/timeline",
            search_placeholder = T("搜索笔记"),
            show_aside = False)

class PublicTimelineHandler(TimelineHandler):
    """公共笔记的时光轴视图"""
    default_type = "public"


xurls = (
    r"/note/timeline", TimelineHandler,
    r"/note/public",   PublicTimelineHandler,
    r"/note/tools/timeline", TimelineHandler,
    r"/note/timeline/month", DateTimeline,
    r"/note/api/timeline", TimelineAjaxHandler
)

