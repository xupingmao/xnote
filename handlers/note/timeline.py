# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/18
# @modified 2020/02/22 21:36:00

"""时光轴视图"""
import re
import xauth
import xutils
import xtables
import xtemplate
from xutils import Storage, dateutil, textutil
from xtemplate import T
from .constant import *

NOTE_DAO = xutils.DAO("note")
MSG_DAO  = xutils.DAO("message")

class TaskGroup(Storage):
    def __init__(self, name = "待办任务"):
        super(TaskGroup, self).__init__()
        self.user = xauth.current_name()
        self.type = 'system'
        self.name = name
        self.icon = "fa-calendar-check-o"
        self.ctime = dateutil.format_time()
        self.mtime = dateutil.format_time()
        self.url  = "/message?tag=task"
        self.priority = 1
        self.size = MSG_DAO.get_message_stat(self.user).task_count

class PlanGroup(TaskGroup):
    """计划类型的笔记, @since 2020/02/16"""
    def __init__(self):
        super(PlanGroup, self).__init__("计划列表")
        self.url = "/note/plan"
        self.size = NOTE_DAO.get_note_stat(self.user).plan_count

def search_group(user_name, words):
    rows = NOTE_DAO.list_group(user_name)
    result = []
    for row in rows:
        if textutil.contains_all(row.name, words):
            result.append(row)
    return result

def split_words(search_key):
    search_key_lower = search_key.lower()
    words = []
    p_start = 0
    for p in range(len(search_key_lower) + 1):
        if p == len(search_key_lower):
            if p > p_start:
                word = search_key_lower[p_start:p]
                words.append(word)
            break

        c = search_key_lower[p]
        if textutil.isblank(c):
            # 空格断字
            if p > p_start:
                word = search_key_lower[p_start:p]
                words.append(word)
            p_start = p + 1
        elif textutil.is_cjk(c):
            # 中日韩字符集
            words.append(c)
            p_start = p + 1
        else:
            # 其他字符
            continue
    # print(words)
    return words


def build_date_result(rows, orderby, sticky_title = False, group_title = False, archived_title = False):
    tmp_result = dict()
    sticky_notes = []
    archived_notes = []
    project_notes = []

    for row in rows:
        if sticky_title and row.priority != None and row.priority > 0:
            sticky_notes.append(row)
            continue

        if archived_title and row.archived == True:
            archived_notes.append(row)
            continue

        if group_title and row.type == "group":
            project_notes.append(row)
            continue
        
        if orderby == "mtime":
            date_time = row.mtime
        else:
            date_time = row.ctime

        title = re.match(r"\d+\-\d+\-\d+", date_time).group(0)
        # 优化返回数据大小
        row.content = ""
        if title not in tmp_result:
            tmp_result[title] = []
        tmp_result[title].append(row)

    result = []

    if len(sticky_notes) > 0:
        result.append(dict(title = u'置顶', children = sticky_notes))

    if len(project_notes) > 0:
        result.append(dict(title = u'项目', children = project_notes))

    for key in tmp_result:
        items = tmp_result[key]
        items.sort(key = lambda x: x[orderby], reverse = True)
        result.append(dict(title = key, children = items))

    if len(archived_notes) > 0:
        result.append(dict(title = u'归档', children = archived_notes))

    return dict(code = 'success', data = result)

def list_search_func(context):
    # 主要是搜索
    offset     = context['offset']
    limit      = context['limit']
    search_key = context['search_key']
    type       = context['type']
    user_name  = context['user_name']
    parent_id  = xutils.get_argument("parent_id", "")
    words      = None
    rows       = []

    if parent_id == "":
        parent_id = None

    if search_key != None and search_key != "":
        # TODO 公共笔记的搜索
        search_key = xutils.unquote(search_key)
        words      = split_words(search_key)
        rows       = NOTE_DAO.search_name(words, user_name, parent_id = parent_id)
        rows       = rows[offset: offset + limit]

    return build_date_result(rows, 'ctime', sticky_title = True, group_title = True)

def list_root_func(context):
    user_name = context['user_name']
    rows      = NOTE_DAO.list_group(user_name)
    rows.insert(0, PlanGroup())
    return build_date_result(rows, 'mtime', sticky_title = True, archived_title = True)

def list_public_func(context):
    offset = context['offset']
    limit  = context['limit']
    rows   = NOTE_DAO.list_public(offset, limit)
    return build_date_result(rows, 'ctime')

def list_sticky_func(context):
    offset    = context['offset']
    limit     = context['limit']
    user_name = context['user_name']
    rows      = NOTE_DAO.list_sticky(user_name, offset, limit)
    return build_date_result(rows, 'ctime')

def list_removed_func(context):
    offset    = context['offset']
    limit     = context['limit']
    user_name = context['user_name']
    rows      = NOTE_DAO.list_removed(user_name, offset, limit)
    return build_date_result(rows, 'ctime')

def list_archived_func(context):
    offset    = context['offset']
    limit     = context['limit']
    user_name = context['user_name']
    rows      = NOTE_DAO.list_archived(user_name, offset, limit)
    return build_date_result(rows, 'ctime')

def list_by_type_func(context):
    type      = context['type']
    offset    = context['offset']
    limit     = context['limit']
    user_name = context['user_name']
    rows      = NOTE_DAO.list_by_type(user_name, type, offset, limit)
    return build_date_result(rows, 'ctime')

def list_plan_func(context):
    offset    = context['offset']
    limit     = context['limit']
    user_name = context['user_name']
    rows      = NOTE_DAO.list_by_type(user_name, 'plan', offset, limit)
    old_task  = TaskGroup("待办任务(旧版)")
    if old_task.size > 0:
        rows.append(old_task)
    return build_date_result(rows, 'ctime')

def list_all_func(context):
    offset    = context['offset']
    limit     = context['limit']
    user_name = context['user_name']
    rows      = NOTE_DAO.list_recent_created(user_name, offset, limit)
    return build_date_result(rows, 'ctime')

def default_list_func(context):
    offset    = context['offset']
    limit     = context['limit']
    user_name = context['user_name']
    parent_id = context['parent_id']
    rows      = NOTE_DAO.list_by_parent(user_name, parent_id, offset, limit, 'ctime')
    return build_date_result(rows, 'ctime', sticky_title = True, group_title = True)

LIST_FUNC_DICT = {
    'root': list_root_func,
    'public': list_public_func,
    'sticky': list_sticky_func,
    'removed': list_removed_func,
    'archived': list_archived_func,
    'md': list_by_type_func,
    'group': list_by_type_func,
    'gallery': list_by_type_func,
    'document': list_by_type_func,
    'html': list_by_type_func,
    'list': list_by_type_func,
    'table': list_by_type_func,
    'csv': list_by_type_func,
    'plan': list_plan_func,
    'all': list_all_func,
    "search": list_search_func,
}

class TimelineAjaxHandler:

    def GET(self):
        offset     = xutils.get_argument("offset", 0, type=int)
        limit      = xutils.get_argument("limit", 20, type=int)
        type       = xutils.get_argument("type", "root")
        parent_id  = xutils.get_argument("parent_id", None, type=str)
        search_key = xutils.get_argument("key", None, type=str)
        user_name  = xauth.current_name()

        list_func = LIST_FUNC_DICT.get(type, default_list_func)
        return list_func(locals())

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
        parent_id   = xutils.get_argument("parent_id", "")
        key         = xutils.get_argument("key", "")
        title       = u"最新笔记"
        show_create = True

        if type == "public":
            show_create = False
        else:
            xauth.check_login()

        title = NOTE_TYPE_DICT.get(type, u"最新笔记")

        search_title = u"笔记"
        file = NOTE_DAO.get_by_id(parent_id)
        
        if file != None:
            title = file.name
            search_title = file.name

        return xtemplate.render("note/page/timeline.html", 
            title = title,
            type  = type,
            file  = file,
            key   = key,
            show_create = show_create,
            search_action = "/note/timeline",
            search_placeholder = T(u"搜索" + search_title),
            search_ext_dict = dict(parent_id = parent_id),
            show_project_link = (parent_id != ""),
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

