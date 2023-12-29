# -*- coding:utf-8 -*-
# Created by xupingmao on 2017/05/18
# @modified 2022/01/27 21:40:22

"""时光轴视图"""
import re
import xutils
from xnote.core import xauth
from xnote.core import xtemplate
import time
import web
from xutils import Storage, dateutil, textutil
from xutils import webutil
from xutils.textutil import split_words
from xnote.core.xtemplate import T
from handlers.note.constant import *
from handlers.message.dao import MessageDao
from handlers.note.dao_api import NoteDao
from handlers.note import note_helper, dao_share
import handlers.note.dao as note_dao
import handlers.note.dao_log as dao_log
from xnote.core import xmanager


class PathLink:

    def __init__(self, name, url):
        self.name = name
        self.url = url

class ListContext(Storage):
    def __init__(self,**kw):
        self.offset = 0
        self.limit = 0
        self.type = ""
        self.parent_id = 0
        self.search_key = ""
        self.orderby = ""
        self.search_tag = ""
        self.filter_tag = "" # 笔记过滤的tag
        self.user_name = ""
        self.user_id = 0
        self.url_type = ""
        self.update(kw)

def get_parent_link(user_name, type, priority=0):
    if priority < 0:
        return PathLink(T("Archived_Project"), "/note/archived")
    if type == "default" or type == "root_notes":
        return PathLink(u"根目录", "/note/timeline?type=group_list&orderby=name")
    if type == "public":
        return None
    return None


class SystemGroup(Storage):
    def __init__(self, name, url, priority=1, icon="fa fa-file-text-o"):
        super(SystemGroup, self).__init__()
        self.user = xauth.current_name()
        self.type = 'system'
        self.icon = icon
        self.name = name
        self.url = url
        self.priority = priority
        self.level = priority
        self.size = 0
        self.mtime = dateutil.format_datetime()


class TaskGroup(Storage):
    def __init__(self, name="待办任务"):
        super(TaskGroup, self).__init__()
        self.user = xauth.current_name()
        self.type = 'system'
        self.name = name
        self.icon = "fa-calendar-check-o"
        self.ctime = dateutil.format_time()
        self.mtime = dateutil.format_time()
        self.url = "/message?tag=task"
        self.priority = 1
        self.level = self.priority
        self.size = MessageDao.get_message_stat(self.user).task_count


class PlanGroup(SystemGroup):
    """计划类型的笔记, @since 2020/02/16"""

    def __init__(self):
        super(PlanGroup, self).__init__(u"计划列表", "/note/plan")
        self.size = NoteDao.get_note_stat(self.user).plan_count


class StickyGroup(SystemGroup):

    def __init__(self):
        super(StickyGroup, self).__init__(u"置顶笔记", "/note/sticky")
        self.size = NoteDao.get_note_stat(self.user).sticky_count
        self.icon = "fa fa-thumb-tack"


class IndexGroup(SystemGroup):

    def __init__(self):
        super(IndexGroup, self).__init__(u"笔记索引", "/note/index")
        self.icon = "fa fa-gear"


class DefaultProjectGroup(SystemGroup):

    def __init__(self, notes):
        super(DefaultProjectGroup, self).__init__(u"默认项目", "/project/default")
        self.icon = "fa fa-th-large"
        self.size = len(notes)


def search_group(user_name, words):
    rows, count = note_dao.list_group_with_count(user_name)
    result = []
    for row in rows:
        if textutil.contains_all(row.name, words):
            result.append(row)
    return result

def build_note_info_for_timeline(note, url_type=""):
    if url_type == "default":
        return
    
    if note.type == "group":
        note.url = "/note/timeline?type=default&parent_id=%s" % note.id


def build_date_result(rows, orderby='ctime', sticky_title=False, group_title=False, archived_title=False, url_type="timeline"):
    tmp_result = dict()
    sticky_notes = []
    archived_notes = []
    group_notes = []

    for row in rows:
        if row.level == None:
            # 可能是虚拟的对象
            row.level = 0

        build_note_info_for_timeline(row, url_type)
        if sticky_title and row.level > 0:
            sticky_notes.append(row)
            continue

        if archived_title and row.archived == True:
            archived_notes.append(row)
            continue

        if group_title and row.type == "group":
            group_notes.append(row)
            continue

        if orderby == "mtime":
            date_time = row.mtime
        else:
            date_time = row.ctime
        
        # MySQL返回 datetime 类型
        date_time = str(date_time)
        title = date_time.split()[0]
        # 优化返回数据大小
        row.content = ""
        if title not in tmp_result:
            tmp_result[title] = []
        tmp_result[title].append(row)

    tmp_sorted_result = []
    for key in tmp_result:
        items = tmp_result[key]
        items.sort(key=lambda x: x[orderby], reverse=True)
        tmp_sorted_result.append(dict(title=key, children=items))
    tmp_sorted_result.sort(key=lambda x: x['title'], reverse=True)

    result = []

    if len(sticky_notes) > 0:
        # sticky_notes.sort(key = lambda x:x[orderby])
        sticky_notes.sort(key = lambda x: x.name)
        result.append(dict(title=u'置顶', children=sticky_notes))

    if len(group_notes) > 0:
        # group_notes.sort(key = lambda x:x[orderby])
        group_notes.sort(key = lambda x: x.name)
        result.append(dict(title=u'笔记本', children=group_notes))

    result += tmp_sorted_result

    if len(archived_notes) > 0:
        archived_notes.sort(key = lambda x:x[orderby])
        result.append(dict(title=u'归档', children=archived_notes))

    return dict(code='success', data=result)


def list_search_func(context: ListContext):
    # 主要是搜索
    offset = context['offset']
    limit = context['limit']
    search_key = context['search_key']
    type = context['type']
    user_name = context['user_name']
    search_tag = context["search_tag"]
    parent_id = xutils.get_argument_int("parent_id")
    words = None
    rows = []

    start_time = time.time()
    if search_key != None and search_key != "":
        # TODO 公共笔记的搜索
        search_key = xutils.unquote(search_key)
        words = split_words(search_key)

        if search_tag == "public":
            rows = note_dao.search_public(words)
        else:
            rows = note_dao.search_name(words, user_name, parent_id=parent_id)

        rows = rows[offset: offset + limit]
        cost_time = time.time() - start_time
        note_dao.add_search_history(user_name, search_key, "note", cost_time)

    return build_date_result(rows, orderby='ctime', sticky_title=True, group_title=True)


def insert_default_project(rows, user_name):
    root_notes = note_dao.list_by_parent(
        user_name, parent_id="0", offset=0, limit=1000, skip_group=True)
    if len(root_notes) > 0:
        rows.insert(0, DefaultProjectGroup(root_notes))


def insert_task_project(rows, user_name):
    rows.insert(0, TaskGroup())


def list_project_func(context):
    offset = context['offset']
    user_name = context['user_name']
    parent_id = context['parent_id']

    if offset > 0:
        rows = []
    else:
        rows = note_dao.list_group(user_name, parent_id=parent_id, orderby="name")
        # 处理默认项目
        insert_default_project(rows, user_name)
        # 处理备忘录
        insert_task_project(rows, user_name)

    return build_date_result(rows, 'name', sticky_title=True, group_title=True, archived_title=True)

def list_root_func(context):
    offset = context['offset']
    user_name = context['user_name']
    if offset > 0:
        rows = []
    else:
        rows = note_dao.list_group(user_name, parent_id=0)
        # 处理默认项目
        insert_default_project(rows, user_name)
        # 处理备忘录
        insert_task_project(rows, user_name)

    return build_date_result(rows, 'mtime', sticky_title=True, group_title=True, archived_title=True)

def list_public_func(context):
    offset = context['offset']
    limit = context['limit']
    rows = note_dao.list_public(offset, limit)
    return build_date_result(rows, 'ctime')


def list_sticky_func(context):
    offset = context['offset']
    limit = context['limit']
    user_name = context['user_name']
    rows = note_dao.list_sticky(user_name, offset, limit)
    return build_date_result(rows, 'ctime', group_title=False)


def list_removed_func(context):
    offset = context['offset']
    limit = context['limit']
    user_name = context['user_name']
    rows = note_dao.list_removed(user_name, offset, limit)
    return build_date_result(rows, 'ctime')


def list_archived_func(context):
    offset = context['offset']
    limit = context['limit']
    user_name = context['user_name']
    rows = note_dao.list_archived(user_name, offset, limit)
    return build_date_result(rows, 'ctime')


def list_by_type_func(context):
    type = context['type']
    offset = context['offset']
    limit = context['limit']
    user_name = context['user_name']
    if type == "group_list":
        type = "group"

    rows = note_dao.list_by_type(user_name, type, offset, limit, orderby="ctime_desc")
    return build_date_result(rows, 'ctime')


def list_plan_func(context):
    offset = context['offset']
    limit = context['limit']
    user_name = context['user_name']
    rows = note_dao.list_by_type(user_name, 'plan', offset, limit)
    old_task = TaskGroup("待办任务(旧版)")
    if old_task.size > 0:
        rows.append(old_task)
    return build_date_result(rows, 'ctime')


def list_all_func(context):
    offset = context['offset']
    limit = context['limit']
    user_name = context['user_name']
    rows = dao_log.list_recent_created(user_name, offset, limit)
    return build_date_result(rows, 'ctime')


def list_recent_edit_func(context):
    offset = context['offset']
    limit = context['limit']
    user_name = context['user_name']
    rows = dao_log.list_recent_edit(user_name, offset, limit)
    return build_date_result(rows, 'mtime')


def default_list_func(context: ListContext):
    offset = context.offset
    limit = context.limit
    user_name = context['user_name']
    parent_id = context.parent_id
    tags = None
    
    if context.filter_tag != "":
        tags = [context.filter_tag]
    
    note_info = note_dao.get_by_id(parent_id)
    if note_info == None:
        return webutil.FailedResult(code="404", message="笔记不存在")
    
    if note_info.creator != user_name:
        # 分享模式
        share_info = dao_share.get_share_by_note_and_to_user(parent_id, user_name)
        if share_info == None:
            return webutil.FailedResult(code="403", message="无查看权限")
    
    rows = note_dao.list_by_parent(creator_id=note_info.creator_id, parent_id=parent_id, offset=offset, limit=limit, orderby = 'ctime_desc', tags=tags)
    
    orderby = "ctime"
    if context.orderby == "name":
        orderby = "name"
    url_type = context.url_type
    return build_date_result(rows, orderby=orderby, sticky_title=True, group_title=True, url_type=url_type)


def list_root_notes_func(context):
    offset = context['offset']
    limit = context['limit']
    user_name = context['user_name']
    rows = note_dao.list_by_parent(
        user_name, 0, offset, limit, orderby='ctime_desc', skip_group=True)
    return build_date_result(rows, 'ctime', sticky_title=True, group_title=True)


LIST_FUNC_DICT = {
    'root': list_root_func,
    'group': list_project_func,
    'public': list_public_func,
    'sticky': list_sticky_func,
    'removed': list_removed_func,
    'archived': list_archived_func,
    'root_notes': list_root_notes_func,

    'recent_edit': list_recent_edit_func,

    'md': list_by_type_func,
    'gallery': list_by_type_func,
    'document': list_by_type_func,
    'html': list_by_type_func,
    'list': list_by_type_func,
    'table': list_by_type_func,
    'csv': list_by_type_func,
    'log': list_by_type_func,
    "group_list": list_by_type_func,

    'plan': list_plan_func,
    'all': list_all_func,
    "search": list_search_func,
}

class TimelineAjaxHandler:

    @xauth.login_required()
    def GET(self):
        offset = xutils.get_argument_int("offset", 0)
        limit = xutils.get_argument_int("limit", 20)
        type = xutils.get_argument_str("type", "root")
        parent_id = xutils.get_argument_int("parent_id")
        search_key = xutils.get_argument_str("key")
        orderby = xutils.get_argument_str("orderby", "mtime_desc")
        search_tag = xutils.get_argument_str("search_tag")
        user_info = xauth.current_user()
        url_type = xutils.get_argument_str("url_type", "timeline")
        assert user_info != None

        kw = ListContext()
        kw.offset = offset
        kw.limit = limit
        kw.type = type
        kw.parent_id = parent_id
        kw.search_key = search_key
        kw.orderby = orderby
        kw.search_tag = search_tag
        kw.user_name = user_info.name
        kw.user_id = user_info.id
        kw.url_type = url_type
        kw.filter_tag = xutils.get_argument_str("filter_tag")

        list_func = LIST_FUNC_DICT.get(type, default_list_func)
        return list_func(kw)


class DateTimelineAjaxHandler:
    @xauth.login_required()
    def GET(self):
        year = xutils.get_argument_str("year", "")
        month = xutils.get_argument_str("month", "")
        if len(month) == 1:
            month = "0" + month
        user_name = xauth.current_name()
        rows = note_dao.list_by_date(
            "ctime", user_name, "%s-%s" % (year, month))
        result = dict()
        for row in rows:
            date = re.match(r"\d+\-\d+", row.ctime).group(0)
            # 优化数据大小
            row.content = ""
            if date not in result:
                result[date] = []
            result[date].append(row)
        return result


class BaseTimelineHandler:

    note_type = "group"
    search_type = "note"
    show_create = True
    check_login = True
    show_recent_btn = False
    show_back_btn = False
    show_create_btn = False
    show_group_btn = False

    def GET(self):
        self.before_get()
        return self.do_get()

    def before_get(self):
        pass

    def handle_type_all(self):
        self.show_create_btn = False
        self.show_group_btn = True
    
    def handle_type_group_list(self):
        self.show_create_btn = False

    def get_handle_by_type(self, type):
        if type == "all":
            return self.handle_type_all
        if type == "group_list":
            return self.handle_type_group_list
        return None

    def do_get(self):
        type = xutils.get_argument_str("type", self.note_type)
        parent_id = xutils.get_argument_str("parent_id", "0")
        key = xutils.get_argument_str("key", "")
        title = u"最新笔记"

        # 检查登录态
        if self.check_login:
            xauth.check_login()

        if type == "search" and key == "":
            raise web.found("/search")

        user_name = xauth.current_name_str()
        title = NOTE_TYPE_DICT.get(type, u"最新笔记")
        title_link = None
        note_priority = 0
        file = NoteDao.get_by_id(parent_id)
    
        handle = self.get_handle_by_type(type)
        if handle != None:
            handle()

        xmanager.add_visit_log(user_name, webutil.get_request_path())

        if file != None:
            title = T("笔记列表")
            title_link = PathLink(file.name, file.url)
            note_priority = file.priority

        pathlist = []
        parent_link = get_parent_link(user_name, type, note_priority)

        if parent_link != None:
            pathlist.append(parent_link)

        if title_link != None:
            pathlist.append(title_link)

        kw = Storage()
        kw.show_aside = False
        kw.show_recent_btn = self.show_recent_btn
        kw.show_back_btn = self.show_back_btn
        kw.show_create_btn = self.show_create_btn
        kw.show_group_btn = self.show_group_btn
        if parent_id == "0":
            kw.show_rename_btn = False
        kw.type = type
        kw.file = file
        kw.title = title
        kw.title_link = title_link
        kw.parent_link = parent_link
        kw.show_create = self.show_create
        kw.search_type = self.search_type
        kw.search_ext_dict = dict(parent_id=parent_id)
        kw.key = key
        kw.pathlist = pathlist
        kw.CREATE_BTN_TEXT_DICT = CREATE_BTN_TEXT_DICT

        return xtemplate.render("note/page/timeline/timeline.html",**kw)


class TimelineHandler(BaseTimelineHandler):
    note_type = "group"
    show_create_btn = True

    def before_get(self):
        parent_id = xutils.get_argument_int("parent_id")
        if parent_id == 0:
            self.show_recent_btn = True


class TimelineRecentHandler(BaseTimelineHandler):
    note_type = "all"
    show_recent_btn = False
    show_back_btn = True
    show_create_btn = False


class PublicTimelineHandler(TimelineHandler):
    """公共笔记的时光轴视图"""
    note_type = "public"
    check_login = False
    show_create = False
    search_type = "note.public"


class GalleryListHandler(BaseTimelineHandler):
    note_type = "gallery"


class TableListHandler(BaseTimelineHandler):
    note_type = "csv"


class HtmlListHandler(BaseTimelineHandler):
    note_type = "html"


class MarkdownListHandler(BaseTimelineHandler):
    note_type = "md"


class DocumentListHandler(BaseTimelineHandler):
    note_type = "document"


class LogListHandler(BaseTimelineHandler):
    note_type = "log"


class ListNoteHandler(BaseTimelineHandler):
    note_type = "list"


class PlanListHandler(BaseTimelineHandler):
    note_type = "plan"


class StickyHandler(BaseTimelineHandler):
    note_type = "sticky"


class RemovedHandler(BaseTimelineHandler):
    note_type = "removed"


class DefaultProjectHandler(BaseTimelineHandler):
    note_type = "root_notes"
    show_create = False


class DateHandler:

    type_order_dict = {
        "group":  0,
        "gallery": 10,
        "list": 20,
        "table": 30,
        "csv": 30,
        "md": 90,
    }

    def sort_notes(self, notes):
        notes.sort(key=lambda x: self.type_order_dict.get(x.type, 100))

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
        show_back = xutils.get_argument("show_back", "")
        date = xutils.get_argument("date", time.strftime("%Y-%m"))

        assert isinstance(user_name, str)
        assert isinstance(date, str)

        xmanager.add_visit_log(
            user_name, "/note/date?show_back=%s" % show_back)

        parts = date.split("-")
        if len(parts) == 2:
            year = int(parts[0])
            month = int(parts[1])
        else:
            year = int(parts[0])
            month = dateutil.get_current_month()

        notes = []
        # 待办任务
        notes.append(MessageDao.get_message_tag(user_name, "task", priority=2))
        notes.append(MessageDao.get_message_tag(user_name, "log",  priority=2))
        notes.append(SystemGroup(
            "我的人生", "/note/view?skey=my_life", priority=2))
        notes.append(SystemGroup("我的年报:%s" % year, "/note/view?skey=year_%s" % year,
                                 priority=2))
        notes.append(SystemGroup("我的月报:%s" % date, "/note/view?skey=month_%s" % date,
                                 priority=2))

        notes_new = note_dao.list_by_date("ctime", user_name, date)
        notes = notes + notes_new
        notes_by_date = note_helper.assemble_notes_by_date(notes)

        kw = Storage()
        kw.html_title = T("我的笔记")
        kw.date = date
        kw.year = year
        kw.month = month
        kw.notes_by_date = notes_by_date
        kw.show_back = show_back
        kw.search_type = "default"

        return xtemplate.render("note/page/list_by_date.html", **kw)


xutils.register_func("note.build_date_result", build_date_result)

xurls = (
    r"/note/api/timeline", TimelineAjaxHandler,

    # 时光轴视图
    r"/note/timeline", TimelineHandler,
    r"/note/timeline/recent", TimelineRecentHandler,
    r"/note/timeline/month", DateTimelineAjaxHandler,
    
    r"/note/plan", PlanListHandler,
    r"/project/default", DefaultProjectHandler,

    # 日期视图
    r"/note/monthly", DateHandler,
)
