# encoding=utf-8
# @since 2016/12
# @modified 2020/02/04 23:20:49
import math
import time
import web
import xutils
import xtemplate
import xtables
import xauth
import xconfig
import xmanager
import os
from xutils import Storage
from xutils import cacheutil, dateutil, fsutil
from xutils.dateutil import Timer
from xtemplate import T

VIEW_TPL   = "note/view.html"
TYPES_NAME = "笔记索引"
NOTE_DAO   = xutils.DAO("note")
MSG_DAO    = xutils.DAO("message")

class PathNode(Storage):

    def __init__(self, name, url, type="note"):
        self.name     = name
        self.url      = url
        self.type     = type
        self.priority = 0
        self.icon     = type

class GroupLink(Storage):
    """笔记本的类型"""

    def __init__(self, name, url, size = None, type="group"):
        self.type     = type
        self.priority = 0
        self.name     = name
        self.url      = url
        self.size     = size
        self.mtime    = ""
        self.ctime    = ""
        self.show_next = True
        self.icon     = "fa-folder orange"

class SystemLink(GroupLink):
    """系统列表项"""

    def __init__(self, name, url, size=None):
        GroupLink.__init__(self, name, url, size, "system")
        self.icon = "icon-folder-system"

class NoteLink:
    def __init__(self, name, url, icon = "fa-cube", size = None):
        self.type = "link"
        self.name = name
        self.url  = url
        self.icon = icon
        self.size = size
        self.priority = 0
        self.ctime = ""
        self.show_next = True

def type_node_path(name, url):
    parent = PathNode(TYPES_NAME, "/note/types")
    return [parent, GroupLink(T(name), url)]

class BaseTimelineHandler:

    @xauth.login_required()
    def GET(self):
        return xtemplate.render("note/timeline.html", 
            title = T(self.title), 
            type = self.note_type,
            search_action = "/note/timeline",
            search_placeholder = "搜索笔记")

class DefaultListHandler:

    @xauth.login_required()
    def GET(self):
        page      = xutils.get_argument("page", 1, type=int)
        user_name = xauth.get_current_name()
        pagesize  = xconfig.PAGE_SIZE
        offset    = (page-1) * pagesize
        files     = NOTE_DAO.list_by_parent(user_name, 0, offset, pagesize)
        amount    = NOTE_DAO.count_by_parent(user_name, 0);
        parent    = NOTE_DAO.get_root()

        return xtemplate.render(VIEW_TPL,
            file_type  = "group",
            back_url   = xconfig.get_user_config(user_name, "HOME_PATH"),
            pathlist   = [parent, Storage(name="默认分类", type="group", url="/note/default")],
            files      = files,
            file       = Storage(id = 1, name="默认分类", type="group", parent_id = 0),
            page       = page,
            page_max   = math.ceil(amount / pagesize),
            groups     = NOTE_DAO.list_group(),
            show_mdate = True,
            page_url   = "/note/default?page=")


class GroupListHandler:

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
        notes = NOTE_DAO.list_by_parent(user_name, 0, orderby = "mtime_desc")
        tools = []
        fixed_books = []
        normal_books = []

        msg_stat  = MSG_DAO.get_message_stat(user_name)
        note_link = NoteLink("待办任务", "/message?tag=task", "fa-calendar-check-o", size = msg_stat.task_count)
        fixed_books.append(note_link)

        # 默认分组处理
        fixed_books.append(SystemLink("笔记索引", "/note/index?source=group"))

        files = fixed_books + notes

        root = NOTE_DAO.get_root()
        return xtemplate.render("note/note_list_page.html", 
            file = root, 
            pathlist = [root],
            show_path_list = True,
            show_size = True,
            files = files)

def load_note_tools(user_name):
    msg_stat  = MSG_DAO.get_message_stat(user_name)
    note_stat = NOTE_DAO.get_note_stat(user_name)

    return [
        NoteLink("任务", "/message?tag=task", "fa-calendar-check-o", size = msg_stat.task_count),
        NoteLink("置顶", "/note/sticky", "fa-thumb-tack", size = note_stat.sticky_count),
        NoteLink("话题", "/search/rules", "fa-search", size = msg_stat.key_count),
        NoteLink("记事", "/message?tag=log", "fa-sticky-note", size = msg_stat.log_count),
        NoteLink("项目", "/note/timeline", "fa-folder", size = note_stat.group_count),
        NoteLink("文档", "/note/document", "fa-file-text", size = note_stat.doc_count),
        NoteLink("相册", "/note/gallery", "fa-image", size = note_stat.gallery_count),
        NoteLink("清单", "/note/list", "fa-list", size = note_stat.list_count),
        NoteLink("表格", "/note/table", "fa-table", size = note_stat.table_count),
        NoteLink("词典", "/note/dict",  "icon-dict", size = note_stat.dict_count),
        # NoteLink("通讯录", "/note/addressbook", "fa-address-book"),
        # NoteLink("富文本", "/note/html", "fa-file-word-o"),
        NoteLink("回收站", "/note/removed", "fa-trash", size = note_stat.removed_count),
        # NoteLink("导入笔记", "/note/html_importer", "fa-cube"),
        NoteLink("按月查看", "/note/date", "fa-cube"),
        NoteLink("数据统计", "/note/stat", "fa-bar-chart"),
        NoteLink("上传管理", "/fs_upload", "fa-upload")
    ]

def load_category(user_name, include_system = False):
    data = NOTE_DAO.list_group(user_name, orderby = "mtime_desc")
    sticky_groups = list(filter(lambda x: x.priority != None and x.priority > 0, data))
    archived_groups = list(filter(lambda x: x.archived == True, data))
    normal_groups = list(filter(lambda x: x not in sticky_groups and x not in archived_groups, data))
    groups_tuple = [
        ("置顶项目", sticky_groups),
        ("普通项目", normal_groups),
        ("归档项目", archived_groups)
    ]

    if include_system:
        system_folders = [
            NoteLink("笔记", "/note/add", "fa-file-text-o"),
            NoteLink("相册", "/note/add?type=gallery", "fa-photo"),
            NoteLink("表格", "/note/add?type=csv", "fa-table"),
            NoteLink("分组", "/note/add?type=group", "fa-folder")
        ]

        default_book_count = NOTE_DAO.count_by_parent(user_name, 0)
        if default_book_count > 0:
            sticky_groups.insert(0, SystemLink("默认分组", "/note/default", default_book_count))
        sticky_groups.insert(0, NoteLink("时光轴", "/note/tools/timeline", "cube"))

        groups_tuple = [
            ("新建", system_folders),
            ("置顶", sticky_groups),
            ("分组", normal_groups),
            ("已归档", archived_groups),
        ]


    return groups_tuple

class GroupSelectHandler:
    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", "")
        callback = xutils.get_argument("callback")
        user_name = xauth.current_name()
        
        filetype = xutils.get_argument("filetype", "")
        groups_tuple = load_category(xauth.current_name())
        web.header("Content-Type", "text/html; charset=utf-8")
        files = NOTE_DAO.list_group(user_name)
        return xtemplate.render("note/component/group_select.html", 
            id = id, 
            groups_tuple = groups_tuple,
            callback = callback,
            files = files)

class CategoryHandler:

    @xauth.login_required()
    def GET(self):
        groups_tuple = load_category(xauth.current_name(), True)
        return xtemplate.render("note/template/category.html", 
            id=id, groups_tuple = groups_tuple)


class RemovedHandler(BaseTimelineHandler):

    title = T("回收站")
    note_type = "removed"

    @xauth.login_required()
    def GET_old(self):
        page = xutils.get_argument("page", 1, type=int)
        user_name = xauth.current_name()

        limit  = xconfig.PAGE_SIZE
        offset = (page-1)*limit

        amount = NOTE_DAO.count_removed(user_name)
        files  = NOTE_DAO.list_removed(user_name, offset, limit)
        parent = PathNode(TYPES_NAME, "/note/types")

        return xtemplate.render(VIEW_TPL,
            pathlist  = [parent, PathNode(T("回收站"), "/note/removed")],
            file_type = "group",
            files     = files,
            page      = page,
            show_aside = True,
            show_mdate = True,
            page_max  = math.ceil(amount / 10),
            page_url  = "/note/removed?page=")


class BaseListHandler:

    note_type = "gallery"
    title     = "相册"
    orderby   = "ctime_desc"

    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        user_name = xauth.current_name()

        limit  = xconfig.PAGE_SIZE
        offset = (page-1)*limit

        amount = NOTE_DAO.count_by_type(user_name, self.note_type)
        files  = NOTE_DAO.list_by_type(user_name, self.note_type, offset, limit, self.orderby)

        # 上级菜单
        parent = PathNode(TYPES_NAME, "/note/types")
        return xtemplate.render(VIEW_TPL,
            pathlist  = [parent, PathNode(self.title, "/note/" + self.note_type)],
            file_type = "group",
            group_type = self.note_type,
            files     = files,
            page      = page,
            show_mdate = True,
            page_max  = math.ceil(amount / xconfig.PAGE_SIZE),
            page_url  = "/note/%s?page=" % self.note_type)


class GalleryListHandler(BaseTimelineHandler):

    def __init__(self):
        self.note_type = "gallery"
        self.title = "相册"
        self.orderby = "ctime_desc"

class TableListHandler(BaseTimelineHandler):

    def __init__(self):
        self.note_type = "csv"
        self.title = "表格"

class AddressBookHandler(BaseListHandler):

    def __init__(self):
        self.note_type = "address"
        self.title = "通讯录"

class HtmlListHandler(BaseListHandler):

    def __init__(self):
        self.note_type = "html"
        self.title = "富文本"

class MarkdownListHandler(BaseTimelineHandler):
    note_type = "md"
    title     = "Markdown"

class DocumentListHandler(BaseTimelineHandler):
    note_type = "document"
    title     = T("文档")

class ListHandler(BaseTimelineHandler):

    def __init__(self):
        self.note_type = "list"
        self.title = "清单"


class TextHandler(BaseListHandler):

    def __init__(self):
        self.note_type = "text"
        self.title = "文本"

class NoteIndexHandler:

    @xauth.login_required()
    def GET(self):
        source = xutils.get_argument("source")
        page = 1

        limit  = xconfig.PAGE_SIZE
        offset = (page-1)*limit

        files = load_note_tools(xauth.current_name())
        amount = len(files)

        if source == "group":
            show_path_list = False
            show_parent_link = True
        else:
            show_path_list = False
            show_parent_link = False

        return xtemplate.render(VIEW_TPL,
            pathlist  = [PathNode(TYPES_NAME, "/note/types")],
            file_type = "group",
            files     = files,
            show_path_list   = show_path_list,
            show_parent_link = show_parent_link,
            show_next  = True,
            show_size  = True,
            search_action = "/note/timeline",
            search_placeholder = "搜索笔记")

class ToolListHandler(NoteIndexHandler):
    pass

class TypesHandler(ToolListHandler):
    """A alias for ToolListHandler"""
    pass

class RecentHandler:
    """show recent notes"""

    def GET(self, orderby = "edit", show_notice = True):
        if not xauth.has_login():
            raise web.seeother("/note/public")
        if xutils.sqlite3 is None:
            raise web.seeother("/fs_list")
        days     = xutils.get_argument("days", 30, type=int)
        page     = xutils.get_argument("page", 1, type=int)
        pagesize = xutils.get_argument("pagesize", xconfig.PAGE_SIZE, type=int)
        page     = max(1, page)
        offset   = max(0, (page-1) * pagesize)
        limit    = pagesize
        time_attr = "ctime"

        show_mdate = False
        show_cdate = False
        show_adate = False
        dir_type   = "recent_edit"

        creator = xauth.get_current_name()
        if orderby == "viewed":
            html_title = "Recent Viewed"
            files = xutils.call("note.list_recent_viewed", creator, offset, limit)
            time_attr = "atime"
            show_adate = True
            dir_type = "recent_viewed"
        elif orderby == "created":
            html_title = "Recent Created"
            files = xutils.call("note.list_recent_created", creator, offset, limit)
            time_attr = "ctime"
            show_cdate = True
            dir_type = "recent_created"
        else:
            html_title = "Recent Updated"
            files = xutils.call("note.list_recent_edit", creator, offset, limit)
            time_attr = "mtime"
            show_mdate = True
            dir_type = "recent_edit"
        
        count   = NOTE_DAO.count_user_note(creator)
        
        return xtemplate.render(VIEW_TPL,
            pathlist  = type_node_path(html_title, ""),
            html_title = html_title,
            file_type  = "group",
            dir_type   = dir_type,
            files = files,
            show_aside = True,
            page = page,
            show_cdate = show_cdate,
            show_mdate = show_mdate,
            show_adate = show_adate,
            page_max    = math.ceil(count/xconfig.PAGE_SIZE), 
            page_url    ="/note/recent_%s?page=" % orderby)

class PublicGroupHandlerOld(BaseTimelineHandler):
    title = T("公共笔记"), 
    note_type = "public"

    def GET_old(self):
        # 老的分页逻辑
        page = xutils.get_argument("page", 1, type=int)
        page = max(1, page)
        offset = (page - 1) * xconfig.PAGE_SIZE
        files = NOTE_DAO.list_public(offset, xconfig.PAGE_SIZE)
        count = NOTE_DAO.count_public()
        return xtemplate.render(VIEW_TPL, 
            show_aside = True,
            pathlist   = [Storage(name="公开笔记", url="/note/public")],
            file_type  = "group",
            dir_type   = "public",
            files      = files,
            page       = page, 
            show_cdate = True,
            groups     = NOTE_DAO.list_group(),
            page_max   = math.ceil(count/xconfig.PAGE_SIZE), 
            page_url   = "/note/public?page=")

def link_by_month(year, month, delta = 0):
    tm = Storage(tm_year = year, tm_mon = month, tm_mday = 0)
    t_year, t_mon, t_day = dateutil.date_add(tm, months = delta)
    return "/note/date?year=%d&month=%02d" % (t_year, t_mon)

class DateHandler:

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
        
        year  = xutils.get_argument("year", time.strftime("%Y"))
        month = xutils.get_argument("month", time.strftime("%m"))
        if len(month) == 1:
            month = '0' + month

        date = year + "-" + month
        created = xutils.call("note.list_by_date", "ctime", user_name, date)
        by_name = xutils.call("note.list_by_date", "name", user_name, year + "_" + month)

        notes = []
        dup = set()
        for v in created + by_name:
            if v.id in dup:
                continue
            dup.add(v.id)
            notes.append(v)

        return xtemplate.render("note/tools/list_by_date.html", 
            link_by_month = link_by_month,
            year = int(year),
            month = int(month),
            notes = notes)

class StickyHandler(BaseTimelineHandler):

    def __init__(self):
        self.note_type = "sticky"
        self.title = T("置顶")

    @xauth.login_required()
    def GET_old(self):
        user  = xauth.current_name()
        files = xutils.call("note.list_sticky", user)
        return xtemplate.render(VIEW_TPL,
            pathlist  = [PathNode("置顶笔记", "/note/sticky")],
            file_type = "group",
            dir_type  = "sticky",
            files     = files,
            show_aside = True,
            show_mdate = True)

class ArchivedHandler:

    @xauth.login_required()
    def GET(self):
        user  = xauth.current_name()
        files = NOTE_DAO.list_archived(user)
        return xtemplate.render(VIEW_TPL,
            pathlist  = [PathNode("归档分组", "/note/archived")],
            file_type = "group",
            dir_type  = "archived",
            files     = files,
            show_mdate = True)

class ManagementHandler:

    @xauth.login_required()
    def GET(self):
        parent_id = xutils.get_argument("parent_id", "0")
        user_name = xauth.current_name()

        if parent_id == "0":
            parent_note = NOTE_DAO.get_root()
        else:
            parent_note = NOTE_DAO.get_by_id(parent_id)
        
        if parent_note is None:
            raise web.seeother("/unauthorized")

        parent_name = parent_note.name
        if parent_note.type == "gallery":
            fpath = fsutil.get_gallery_path(parent_note)
            pathlist = fsutil.listdir_abs(fpath)
            return xtemplate.render("note/admin/gallery.html", 
                note = parent_note, 
                dirname = fpath, 
                pathlist = pathlist)
        notes = NOTE_DAO.list_by_parent(user_name, parent_id, 0, 200)
        parent = Storage(url = "/note/%s" % parent_id, name = parent_name)
        current = Storage(url = "#", name = "整理")
        return xtemplate.render("note/management.html", 
            pathlist = NOTE_DAO.list_path(parent_note),
            files = notes,
            show_path = True,
            current = current,
            parent = parent)

xurls = (
    r"/note/group"          , GroupListHandler,
    r"/note/group_list"     , GroupListHandler,
    r"/note/books"          , GroupListHandler,
    r"/note/category"       , CategoryHandler,
    r"/note/default"        , DefaultListHandler,
    r"/note/ungrouped"      , DefaultListHandler,
    # r"/note/public"         , PublicGroupHandler,
    r"/note/removed"        , RemovedHandler,
    r"/note/archived"       , ArchivedHandler,
    r"/note/sticky"         , StickyHandler,
    r"/note/recent_(created)" , RecentHandler,
    r"/note/recent_edit"    , RecentHandler,
    r"/note/recent_(viewed)", RecentHandler,
    r"/note/group/select"   , GroupSelectHandler,
    r"/note/date"           , DateHandler,
    r"/note/monthly"        , DateHandler,
    r"/note/management"     , ManagementHandler,

    # 笔记分类
    r"/note/gallery"        , GalleryListHandler,
    r"/note/table"          , TableListHandler,
    r"/note/csv"            , TableListHandler,
    
    r"/note/document"       , DocumentListHandler,
    r"/note/html"           , HtmlListHandler,
    r"/note/md"             , MarkdownListHandler,

    r"/note/addressbook"    , AddressBookHandler,
    r"/note/list"           , ListHandler,
    r"/note/text"           , TextHandler,
    r"/note/tools"          , ToolListHandler,
    r"/note/types"          , TypesHandler,
    r"/note/index"          , NoteIndexHandler
)

