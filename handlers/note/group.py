# encoding=utf-8
# @since 2016/12
# @modified 2021/03/21 18:28:29
import math
import time
import web
import xutils
import xtemplate
import xtables
import xauth
import xuserconfig
import xconfig
import xmanager
import os
from xutils import Storage
from xutils import cacheutil, dateutil, fsutil
from xutils.dateutil import Timer
from xtemplate import T
from .constant import CREATE_BTN_TEXT_DICT


VIEW_TPL   = "note/page/view.html"
TYPES_NAME = "笔记索引"
NOTE_DAO   = xutils.DAO("note")
MSG_DAO    = xutils.DAO("message")
PLUGIN     = xutils.Module("plugin")

SEARCH_DOC_DICT = dict(
    search_action = "/note/timeline",
    search_placeholder = u"搜索笔记"
)

class NoteCategory:

    def __init__(self, code, name):
        self.name = "%s-%s" % (code, name)
        self.url  = "/note/group?category=" + code
        self.icon = ""
        self.priority = 0
        self.is_deleted = 0
        self.size = 0
        self.show_next = True
        self.icon = "fa-folder"

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
    def __init__(self, name, url, icon = "fa-cube", size = None, roles = None, category = "000"):
        self.type = "link"
        self.name = T(name)
        self.url  = url
        self.icon = icon
        self.size = size
        self.priority = 0
        self.ctime = ""
        self.hide  = False
        self.show_next  = True
        self.is_deleted = 0
        self.category = category

        # 角色
        if roles is None:
            roles = ("admin", "user")
        self.roles = roles

    def __str__(self):
        return str(self.__dict__)

class DictEntryLink(NoteLink):
    def __init__(self, size):
        NoteLink.__init__(self, "词典", "/note/dict",  "icon-dict", size = size)
        self.hide = xconfig.HIDE_DICT_ENTRY


class NoteCard:

    def __init__(self, title, rows):
        self.title = title
        self.rows  = rows

class RecentGroup:

    def __init__(self, user_name):
        self.name = u"最近"
        self.size = None
        self.url  = "/note/recent?orderby=create"
        self.icon = "fa-history"
        self.priority  = 0
        self.show_next = True
        self.is_deleted = 0


def type_node_path(name, url):
    parent = PathNode(TYPES_NAME, "/note/types")
    return [parent, GroupLink(T(name), url)]


class DefaultListHandler:

    @xauth.login_required()
    def GET(self):
        page      = xutils.get_argument("page", 1, type=int)
        user_name = xauth.get_current_name()
        pagesize  = xconfig.PAGE_SIZE
        offset    = (page-1) * pagesize
        files     = NOTE_DAO.list_default_notes(user_name, offset, pagesize)
        amount    = NOTE_DAO.count_by_parent(user_name, 0);
        parent    = NOTE_DAO.get_root()

        return xtemplate.render("note/page/note_default.html",
            notes      = files,
            page       = page,
            page_max   = math.ceil(amount / pagesize),
            page_url   = "/note/default?page=")

def get_category_list():
    # TODO 配置化
    # 主要参考的是：杜威十进制分类法和国际十进制分类法
    category_list = []
    category_list.append(NoteCategory("000", "知识和分类"))
    category_list.append(NoteCategory("100", "哲学和心理学"))
    category_list.append(NoteCategory("200", "宗教"))
    category_list.append(NoteCategory("300", "社会科学"))
    category_list.append(NoteCategory("400", "个人记事"))
    category_list.append(NoteCategory("500", "数学和自然科学"))
    category_list.append(NoteCategory("600", "应用科学、医学、技术"))
    category_list.append(NoteCategory("700", "艺术与休闲"))
    category_list.append(NoteCategory("800", "语言和文学"))
    category_list.append(NoteCategory("900", "历史、地理和传记"))
    return category_list

class GroupListHandler:

    @xauth.login_required()
    def GET(self):
        category  = xutils.get_argument("category")
        user_name = xauth.current_name()
        notes     = NOTE_DAO.list_group(user_name, orderby = "name")
        sticky_groups   = list(filter(lambda x:x.priority > 0, notes))
        archived_groups = list(filter(lambda x: x.archived == True, notes))
        normal_groups   = list(filter(lambda x: x not in archived_groups and x not in sticky_groups, notes))

        tools        = []
        fixed_books  = []
        normal_books = []

        xmanager.add_visit_log(user_name, "/note/group")

        # 短消息：任务、通知和备忘
        fixed_books.append(MSG_DAO.get_message_tag(user_name, "task"))
        fixed_books.append(MSG_DAO.get_message_tag(user_name, "log"))

        # 未分类信息
        files = NOTE_DAO.list_by_parent(user_name, 0, 0, 1000, skip_group = True)
        if len(files) > 0:
            fixed_books.append(NoteLink("默认笔记本", "/note/default", size=len(files), icon = "fa-th-large"))

        if len(archived_groups) > 0:
            fixed_books.append(NoteLink("归档笔记本", "/note/archived", size = len(archived_groups), icon = "fa-th-large"))

        files = fixed_books + normal_groups
        root  = NOTE_DAO.get_root()

        group_cards = [
            ("", fixed_books),
            ("置顶", sticky_groups),
            ("笔记本", normal_groups),
            ("归档", archived_groups),
        ]

        return xtemplate.render("note/page/group_list.html", 
            file = root, 
            title = u"我的笔记",
            pathlist = [root],
            show_path_list = True,
            show_size = True,
            parent_id = 0,
            files = files,
            group_cards = group_cards,
            search_type = "note")

def load_note_index(user_name):
    msg_stat  = MSG_DAO.get_message_stat(user_name)
    note_stat = NOTE_DAO.get_note_stat(user_name)

    return [
        NoteCard("分类", [
            NoteLink("任务", "/message?tag=task", "fa-calendar-check-o", size = msg_stat.task_count),
            NoteLink("备忘", "/message?tag=log", "fa-sticky-note", size = msg_stat.log_count),
            NoteLink("项目", "/note/group", "fa-folder", size = note_stat.group_count),
            NoteLink("文档", "/note/document", "fa-file-text", size = note_stat.doc_count),
            NoteLink("相册", "/note/gallery", "fa-image", size = note_stat.gallery_count),
            NoteLink("清单", "/note/list", "fa-list", size = note_stat.list_count),
            NoteLink("表格", "/note/table", "fa-table", size = note_stat.table_count),
            NoteLink("日志", "/note/log", "fa-file-text", size = note_stat.log_count),
            DictEntryLink(size = note_stat.dict_count),
            NoteLink("插件", "/plugins_list", "fa-th-large", size = len(xconfig.PLUGINS_DICT), roles = ["admin"]),
        ]),
        
        NoteCard(u"工具", [
            NoteLink("置顶笔记", "/note/sticky", "fa-thumb-tack", size = note_stat.sticky_count),
            NoteLink("搜索历史", "/search", "fa-search", size = None),
            NoteLink("导入笔记", "/note/html_importer", "fa-internet-explorer"),
            # NoteLink("日历视图", "/note/calendar", "fa-calendar"),
            NoteLink("时间视图", "/note/date", "fa-calendar"),
            NoteLink("数据统计", "/note/stat", "fa-bar-chart"),
            NoteLink("上传管理", "/fs_upload", "fa-upload"),
            NoteLink("回收站", "/note/removed", "fa-trash", size = note_stat.removed_count),
        ])
    ]

def load_category(user_name, include_system = False):
    data = NOTE_DAO.list_group(user_name, orderby = "name")
    sticky_groups   = list(filter(lambda x: x.priority != None and x.priority > 0, data))
    archived_groups = list(filter(lambda x: x.archived == True, data))
    normal_groups   = list(filter(lambda x: x not in sticky_groups and x not in archived_groups, data))
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
        files = get_category_list()

        root = NOTE_DAO.get_root()
        return xtemplate.render("note/page/category.html", 
            file = root, 
            title = u"目录",
            pathlist = [root],
            show_path_list = True,
            show_size = True,
            parent_id = 0,
            files = files,
            **SEARCH_DOC_DICT)


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
            show_pagination = True,
            show_mdate = True,
            page_max  = math.ceil(amount / xconfig.PAGE_SIZE),
            page_url  = "/note/%s?page=" % self.note_type)


class TextListHandler(BaseListHandler):

    def __init__(self):
        self.note_type = "text"
        self.title = "文本"

class AddressBookListHandler(BaseListHandler):
    def __init__(self):
        self.note_type = "address"
        self.title     = "通讯录"

class NoteIndexHandler:

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
        plugins  = PLUGIN.find_plugins("note")
        template = "note/page/note_tools.html"

        xmanager.add_visit_log(user_name, "/note/tools")

        return xtemplate.render(template,
            html_title = T("笔记工具"),
            plugins     = plugins,
            search_type = "plugin")


class NoteToolHandler(NoteIndexHandler):
    pass

class RecentHandler:
    """最近的笔记"""
    def GET(self, show_notice = True):
        if not xauth.has_login():
            raise web.seeother("/note/public")
        if xutils.sqlite3 is None:
            raise web.seeother("/fs_list")

        page     = xutils.get_argument("page", 1, type=int)
        pagesize = xutils.get_argument("pagesize", xconfig.PAGE_SIZE, type=int)
        orderby  = xutils.get_argument("orderby", "create")
        page     = max(1, page)
        offset   = max(0, (page-1) * pagesize)
        limit    = pagesize
        time_attr = "ctime"

        show_mdate = False
        show_cdate = False
        show_adate = False
        show_action_time = False
        show_hot_index = False
        dir_type   = "recent_edit"

        creator = xauth.get_current_name()
        if orderby == "all":
            html_title = "All"
            files = NOTE_DAO.list_recent_events(creator, offset, limit)
            show_action_time = True
        elif orderby == "view":
            html_title = "Recent Viewed"
            files = NOTE_DAO.list_recent_viewed(creator, offset, limit)
            show_adate = True
            dir_type = "recent_viewed"
        elif orderby == "create":
            html_title = "Recent Created"
            files = NOTE_DAO.list_recent_created(creator, offset, limit)
            time_attr = "ctime"
            show_cdate = True
            dir_type = "recent_created"
        elif orderby == "hot":
            html_title = "Hot"
            files = NOTE_DAO.list_hot(creator, offset, limit)
            show_hot_index = True
        else:
            html_title = "Recent Updated"
            files = NOTE_DAO.list_recent_edit(creator, offset, limit)
            time_attr = "mtime"
            show_mdate = True
            dir_type = "recent_edit"
        
        count   = NOTE_DAO.count_user_note(creator)
        
        return xtemplate.render("note/page/note_recent.html",
            pathlist  = type_node_path(html_title, ""),
            html_title = html_title,
            file_type  = "group",
            dir_type   = dir_type,
            files = files,
            show_aside = False,
            show_size  = False,
            page = page,
            time_attr  = time_attr,
            show_cdate = show_cdate,
            show_mdate = show_mdate,
            show_adate = show_adate,
            show_next  = False,
            show_action_time = show_action_time,
            show_hot_index = show_hot_index,
            page_max    = math.ceil(count/xconfig.PAGE_SIZE), 
            page_url    = "/note/recent_%s?page=" % orderby,
            **SEARCH_DOC_DICT)

class ArchivedHandler:

    @xauth.login_required()
    def GET(self):
        user  = xauth.current_name()
        files = NOTE_DAO.list_archived(user)
        return xtemplate.render("note/page/group_list_archived.html",
            title      = "Archived_Project",
            parent_id  = -1,
            show_size  = True,
            pathlist   = [PathNode("Archived_Project", "/note/archived")],
            file_type  = "group",
            dir_type   = "archived",
            files      = files,
            show_mdate = False)

class ManagementHandler:

    @xauth.login_required()
    def GET(self):
        parent_id = xutils.get_argument("parent_id", "0")
        user_name = xauth.current_name()

        xmanager.add_visit_log(user_name, "/note/management")

        if parent_id == "0" or parent_id is None:
            parent_note = NOTE_DAO.get_root()
            notes = NOTE_DAO.list_group(user_name, orderby = "name", skip_archived = True)
            parent = Storage(url = "/note/group", name = parent_note.name)
        elif parent_id == "default":
            parent_note = NOTE_DAO.get_default_group()
            notes = NOTE_DAO.list_default_notes(user_name)
        else:
            parent_note = NOTE_DAO.get_by_id(parent_id)
            if parent_note == None:
                raise web.notfound()
            notes = NOTE_DAO.list_by_parent(user_name, parent_id, 0, 200, orderby = "ctime_desc")
            parent = Storage(url = "/note/%s" % parent_id, name = parent_note.name)
        
        if parent_note is None:
            raise web.seeother("/unauthorized")

        parent_name = parent_note.name
        if parent_note.type == "gallery":
            fpath = NOTE_DAO.get_gallery_path(parent_note)
            pathlist = fsutil.listdir_abs(fpath)
            return xtemplate.render("note/page/batch/gallery_management.html", 
                note = parent_note, 
                dirname = fpath, 
                pathlist = pathlist)

        current = Storage(url = "#", name = "整理")
        return xtemplate.render("note/page/batch/management.html", 
            pathlist = NOTE_DAO.list_path(parent_note),
            files = notes,
            show_path = True,
            parent_id = parent_id,
            current = current,
            parent  = parent_note)


xurls = (
    r"/note/group"          , GroupListHandler,
    r"/note/group_list"     , GroupListHandler,
    r"/note/books"          , GroupListHandler,
    r"/note/category"       , CategoryHandler,
    r"/note/default"        , DefaultListHandler,
    r"/note/ungrouped"      , DefaultListHandler,
    r"/note/archived"       , ArchivedHandler,
    r"/note/recent_edit"    , RecentHandler,
    r"/note/recent"         , RecentHandler,
    r"/note/recent_(created)" , RecentHandler,
    r"/note/recent_(viewed)", RecentHandler,
    r"/note/group/select"   , GroupSelectHandler,
    r"/note/management"     , ManagementHandler,

    r"/note/text"           , TextListHandler,
    r"/note/tools"          , NoteIndexHandler,
    r"/note/types"          , NoteIndexHandler,
    r"/note/index"          , NoteIndexHandler,
)

