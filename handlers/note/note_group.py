# encoding=utf-8
# @since 2016/12
# @modified 2022/04/22 23:30:02
import math
import time
import copy
import logging

import web
import xutils
import xtemplate
import xauth
import xconfig
import xmanager
from xutils import Storage
from xutils import dateutil, fsutil
from xtemplate import T
from .constant import CREATE_BTN_TEXT_DICT


VIEW_TPL   = "note/page/view.html"
TYPES_NAME = "笔记索引"
NOTE_DAO   = xutils.DAO("note")
MSG_DAO    = xutils.DAO("message")
PLUGIN     = xutils.Module("plugin")
SMART_GROUP_COUNT = 0

def SmartNote(name, url, icon = "fa-folder", size = None, size_attr = None):
    note = Storage(name = name, url = url)
    note.priority = 0
    note.icon = icon
    note.size = size
    note.size_attr = size_attr
    return note

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
        self.badge_info = ""

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
    def __init__(self, name, url, icon = "fa-cube", size = None, roles = None, category = "000", priority = 0):
        self.type = "link"
        self.name = T(name)
        self.url  = url
        self.icon = icon
        self.size = size
        self.priority = priority
        self.ctime = ""
        self.hide  = False
        self.show_next  = True
        self.is_deleted = 0
        self.category = category
        self.badge_info = ""

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

def load_smart_groups_template():
    config = fsutil.load_ini_config("config/note/smart_group.ini")
    result = []
    for key in config.sections:
        item = config.items[key]
        if item.visible == "false":
            continue
        note = SmartNote(item.name, item.url, size_attr = item.size_attr)
        result.append(note)
    return result

_smart_groups = load_smart_groups_template()
def list_smart_group(user_name):
    global SMART_GROUP_COUNT

    note_stat = NOTE_DAO.get_note_stat(user_name)
    smart_group_list = copy.deepcopy(_smart_groups)

    for item in smart_group_list:
        if item.size_attr != None:
            size = getattr(note_stat, item.size_attr)
            item.size = size
            item.badge_info = size

    SMART_GROUP_COUNT = len(smart_group_list)
    return smart_group_list

def count_smart_group(user_name = None):
    return SMART_GROUP_COUNT

class DefaultListHandler:

    @xauth.login_required()
    def GET(self):
        page      = xutils.get_argument("page", 1, type=int)
        user_name = xauth.get_current_name()
        pagesize  = xconfig.PAGE_SIZE
        offset    = (page-1) * pagesize
        files     = NOTE_DAO.list_default_notes(user_name, offset, pagesize)
        amount    = NOTE_DAO.count_by_parent(user_name, 0);

        return xtemplate.render("note/page/note_default.html",
            notes      = files,
            page       = page,
            page_max   = math.ceil(amount / pagesize),
            page_url   = "/note/default?page=")


class ShareListHandler:

    share_type = "public"
    title      = T("公开分享")

    def list_notes(self, user_name, offset, limit):
        orderby = xutils.get_argument("tab", "ctime_desc")
        notes = NOTE_DAO.list_public(offset, limit, orderby)
        for note in notes:
            if orderby == "hot":
                note.badge_info = note.hot_index
            else:
                note.badge_info = dateutil.format_date(note.share_time)
        return notes

    def count_notes(self, user_name):
        return NOTE_DAO.count_public()

    def GET(self):
        page      = xutils.get_argument("page", 1, type=int)
        tab       = xutils.get_argument("tab", "")
        user_name = xauth.get_current_name()
        limit     = xconfig.PAGE_SIZE
        offset    = (page-1) * limit
        
        files     = self.list_notes(user_name, offset, limit)
        amount    = self.count_notes(user_name)

        xmanager.add_visit_log(user_name, "/note/%s" % self.share_type)
        page_url = "/note/{share_type}?tab={tab}&page=".format(
            share_type=self.share_type, tab = tab)

        return xtemplate.render("note/page/note_share.html",
            title      = self.title,
            notes      = files,
            page       = page,
            page_max   = math.ceil(amount / limit),
            page_url   = page_url)

class PublicListHandler(ShareListHandler):
    pass

class ShareToMeListHandler(ShareListHandler):
    
    share_type = "share_to_me"
    title   = T("分享给我")
    orderby = "ctime_desc"

    def count_notes(self, user_name):
        return NOTE_DAO.count_share_to(user_name)

    def list_notes(self, user_name, offset, limit):
        return NOTE_DAO.list_share_to(user_name, offset, limit, self.orderby)

def get_ddc_category_list():
    # TODO 配置化
    # 主要参考的是：杜威十进制分类法和国际十进制分类法
    category_list = []
    category_list.append(NoteCategory("000", "计算机科学、资讯和总类"))
    category_list.append(NoteCategory("100", "哲学和心理学"))
    category_list.append(NoteCategory("200", "宗教"))
    category_list.append(NoteCategory("300", "社会科学"))
    category_list.append(NoteCategory("400", "语言"))
    category_list.append(NoteCategory("500", "数学和自然科学"))
    category_list.append(NoteCategory("600", "应用科学、医学、技术"))
    category_list.append(NoteCategory("700", "艺术与休闲"))
    category_list.append(NoteCategory("800", "文学"))
    category_list.append(NoteCategory("900", "历史、地理和传记"))
    return category_list

class GroupListHandler:

    def load_group_list(self, user_name, status):
        if status in ("active", "archived"):
            notes = NOTE_DAO.list_group(user_name, 
                status = status, orderby = "default")
        else:
            notes = NOTE_DAO.list_smart_group(user_name)

        if status == "active":
            group = NOTE_DAO.get_virtual_group(user_name, "ungrouped")
            if group.size > 0:
                notes.insert(0, group)

        return notes

    def handle_badge_info(self, notes, tab):
        if tab in ("active", "archived"):
            for note in notes:
                note.badge_info = note.children_count

    def sort_notes(self, notes, kw):
        tab = kw.tab
        orderby = kw.orderby

        if tab == "smart":
            return

        kw.show_orderby = True
        
        if orderby == "name_desc":
            notes.sort(key = lambda x:x.name, reverse = True)

        if orderby == "name_asc":
            notes.sort(key = lambda x:x.name)

        if orderby == "hot_desc":
            for note in notes:
                note.hot_index = note.hot_index or 0
                note.badge_info = "热度(%s)" % note.hot_index
            notes.sort(key = lambda x:x.hot_index, reverse = True)

        if orderby == "size_desc":
            for note in notes:
                note.badge_info = note.children_count

            notes.sort(key = lambda x:x.children_count or 0, reverse = True)

        if orderby == "ctime_desc":
            for note in notes:
                note.ctime = note.ctime or ""
                note.badge_info = dateutil.format_date(note.ctime)
            notes.sort(key = lambda x:x.ctime, reverse = True)

        notes.sort(key = lambda x:x.priority, reverse = True)

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()        
        orderby_default = xconfig.get_user_config(user_name, "group_list_order_by", "name_asc")
        logging.debug("orderby_default:%s", orderby_default)

        category  = xutils.get_argument("category")
        tab    = xutils.get_argument("tab", "active")
        orderby   = xutils.get_argument("orderby", orderby_default)
        user_name = xauth.current_name()
        show_back = xutils.get_argument("show_back", type = bool)

        xmanager.add_visit_log(user_name, "/note/group")

        if orderby != orderby_default:
            xconfig.update_user_config(user_name, "group_list_order_by", orderby)

        root  = NOTE_DAO.get_root()
        notes = self.load_group_list(user_name, tab)

        kw = Storage()
        kw.tab     = tab
        kw.orderby = orderby
        kw.title   = T("我的笔记本")
        kw.file    = root
        kw.groups  = notes
        kw.parent_id = 0
        kw.show_back = show_back
        kw.archived_count = NOTE_DAO.count_group(user_name, status = "archived")
        kw.active_count   = NOTE_DAO.count_group(user_name, status = "active")
        kw.smart_count    = SMART_GROUP_COUNT

        self.handle_badge_info(notes, tab = tab)
        self.sort_notes(notes, kw)

        if tab == "smart":
            kw.show_note_types = False

        return xtemplate.render("note/page/group_list.html", **kw)

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
        files = get_ddc_category_list()
        cat_type = xutils.get_argument("type", "ddc")

        root = NOTE_DAO.get_root()
        return xtemplate.render("note/page/category.html", 
            file = root, 
            title = u"杜威十进制分类法(DDC)",
            pathlist = [root],
            show_path_list = True,
            show_size = True,
            parent_id = 0,
            files = files)


class BaseListHandler:

    note_type     = "gallery"
    title         = "相册"
    orderby       = "ctime_desc"
    create_type   = ""
    create_text   = T("创建笔记")
    date_type     = "cdate"
    show_ext_info = True

    def count_notes(self, user_name):
        return NOTE_DAO.count_by_type(user_name, self.note_type)

    def list_notes(self, user_name, offset, limit):
        return NOTE_DAO.list_by_type(user_name, self.note_type, offset, limit, self.orderby)

    def map_notes(self, notes):
        for note in notes:
            note.badge_info = dateutil.format_date(note.ctime)

        return notes

    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        user_name = xauth.current_name()


        limit  = xconfig.PAGE_SIZE
        offset = (page-1)*limit

        amount = self.count_notes(user_name)
        notes  = self.list_notes(user_name, offset, limit)
        notes  = self.map_notes(notes)

        kw = Storage()
        kw.show_ext_info   = self.show_ext_info
        kw.show_pagination = True
        kw.page            = page
        kw.page_max        = math.ceil(amount / xconfig.PAGE_SIZE)
        kw.page_url        = "/note/%s?page=" % self.note_type
        kw.parent_id       = "0"
        kw.notes           = notes

        # 上级菜单
        parent = PathNode(T("根目录"), "/note/group")
        return xtemplate.render("note/page/note_list.html",
            pathlist  = [parent, PathNode(self.title, "/note/" + self.note_type)],
            file_type = "group",
            title     = self.title,
            group_type = self.note_type,
            date_type = self.date_type,
            show_group_option = False,
            create_text = self.create_text,
            create_type = self.create_type,
            **kw)


class TextListHandler(BaseListHandler):

    note_type = "text"
    title = "文本"

class AddressBookListHandler(BaseListHandler):
    
    note_type = "address"
    title     = "通讯录"


class DocumentListHandler(BaseListHandler):

    note_type = "document"
    create_type = "md"
    create_text = T("创建文档")
    title     = "我的文档"

class GalleryListHandler(BaseListHandler):

    note_type = "gallery"
    create_type = "gallery"
    create_text = "创建相册"
    title     = "我的相册"


class CheckListHandler(BaseListHandler):

    note_type = "list"
    create_type = "list"
    create_text = T("创建清单")
    title = T("我的清单")


class TableListHandler(BaseListHandler):

    note_type = "table"
    create_type = "csv"
    create_text = T("创建表格")
    title = T("我的表格")

class RemovedListHandler(BaseListHandler):

    note_type = "removed"
    title     = T("回收站")

    def count_notes(self, user_name):
        return NOTE_DAO.count_removed(user_name)

    def list_notes(self, user_name, offset, limit):
        return NOTE_DAO.list_removed(user_name, offset, limit, self.orderby)

    def map_notes(self, notes):
        for note in notes:
            note.badge_info = dateutil.format_date(note.dtime)
        return notes

class StickyListHandler(BaseListHandler):

    note_type = "sticky"
    title = T("我的置顶")

    def count_notes(self, user_name):
        note_stat = NOTE_DAO.get_note_stat(user_name)
        if note_stat:
            return note_stat.sticky_count
        else:
            return 0

    def list_notes(self, user_name, offset, limit):
        return NOTE_DAO.list_sticky(user_name, offset, limit)

class LogListHandler(BaseListHandler):

    note_type = "log"
    title = T("我的日志")

class HtmlListHandler(BaseListHandler):

    note_type = "html"
    title = T("我的富文本")

class FormListHandler(BaseListHandler):

    note_type = "form"
    title = T("我的表单")

class AllNoteListHandler(BaseListHandler):

    note_type = "all"
    title = T("我的笔记")
    show_ext_info = False

    def count_notes(self, user_name):
        note_stat = NOTE_DAO.get_note_stat(user_name)
        if note_stat:
            return note_stat.total
        else:
            return 0

class NotePluginHandler:

    @xauth.login_required()
    def GET(self):
        raise web.found("/plugin_list?category=note&show_back=true")

class RecentHandler:
    """最近的笔记/常用的笔记"""

    def count_note(self, user_name, orderby):
        return NOTE_DAO.count_visit_log(user_name)

    def list_notes(self, creator, offset, limit, orderby):
        if orderby == "all":
            return NOTE_DAO.list_recent_events(creator, offset, limit)
        elif orderby == "view":
            return NOTE_DAO.list_recent_viewed(creator, offset, limit)
        elif orderby == "create":
            return NOTE_DAO.list_recent_created(creator, offset, limit)
        elif orderby == "myhot":
            return NOTE_DAO.list_hot(creator, offset, limit)

        # 最近更新的
        notes = NOTE_DAO.list_recent_edit(creator, offset, limit)
        for note in notes:
            note.badge_info = dateutil.format_date(note.mtime)
        return notes

    def get_html_title(self, orderby):
        if orderby == "all":
            return "All"

        if orderby == "view":
            return "Recent Viewed"

        if orderby == "create":
            return "Recent Created"
        
        if orderby == "myhot":
            return "Hot"
        
        return "Recent Updated"

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
        dir_type = "recent_edit"
        creator = xauth.get_current_name()

        xmanager.add_visit_log(creator, "/note/recent?orderby=%s" % orderby)

        html_title = self.get_html_title(orderby)
        files = self.list_notes(creator, offset, limit, orderby)
        count = self.count_note(creator, orderby)
        
        return xtemplate.render("note/page/note_recent.html",
            pathlist  = type_node_path(html_title, ""),
            html_title = html_title,
            file_type  = "group",
            dir_type   = dir_type,
            search_type = "note",
            files = files,
            show_aside = False,
            show_size  = False,
            page = page,
            show_next  = False,
            page_max    = math.ceil(count/xconfig.PAGE_SIZE), 
            page_url    = "/note/recent?orderby=%s&page=" % orderby)

class ArchivedHandler:

    @xauth.login_required()
    def GET(self):
        raise web.found("/note/group?tab=archived")

class ManagementHandler:
    """批量管理处理器"""

    def handle_root(self, kw):
        user_name = kw.user_name
        parent_note = NOTE_DAO.get_root()
        notes = NOTE_DAO.list_group(user_name, orderby = "name", 
            skip_archived = True)
        parent = Storage(url = "/note/group", name = parent_note.name)
        
        kw.parent_note = parent_note
        kw.parent = parent
        kw.notes = notes

    def handle_group(self, kw):
        parent_id = kw.parent_id
        user_name = kw.user_name

        parent_note = NOTE_DAO.get_by_id(parent_id)
        if parent_note == None:
            raise web.notfound()
        
        notes = NOTE_DAO.list_by_parent(user_name, parent_id, 
            0, 200, orderby = parent_note.orderby)
        
        parent = Storage(url = "/note/%s" % parent_id, 
            name = parent_note.name)

        kw.parent_note = parent_note
        kw.parent = parent
        kw.notes = notes

    def handle_default(self, kw):
        user_name = kw.user_name
        parent_note = NOTE_DAO.get_default_group()
        notes = NOTE_DAO.list_default_notes(user_name)

        kw.parent_note = parent_note
        kw.notes = notes

    @xauth.login_required()
    def GET(self):
        parent_id = xutils.get_argument("parent_id", "0")
        user_name = xauth.current_name()

        xmanager.add_visit_log(user_name, "/note/management")

        kw = Storage(user_name = user_name, parent_id = parent_id)

        if parent_id == "0" or parent_id is None:
            self.handle_root(kw)
        elif parent_id == "default":
            self.handle_default(kw)
        else:
            self.handle_group(kw)
        
        parent_note = kw.parent_note
        parent = kw.parent
        notes = kw.notes
        
        if parent_note is None:
            raise web.seeother("/unauthorized")

        parent_name = parent_note.name
        if parent_note.type == "gallery":
            fpath = NOTE_DAO.get_gallery_path(parent_note)
            pathlist = fsutil.listdir_abs(fpath, False)
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

class NoteIndexHandler:

    def find_class(self):
        user_name = xauth.current_name()
        home_path = xconfig.get_user_config(user_name, "HOME_PATH")
        clazz = xutils.lookup_func("url:" + home_path)
        if clazz is None:
            return GroupListHandler
        return clazz

    def GET(self):
        clazz = self.find_class()
        return clazz().GET()

    def POST(self):
        clazz = self.find_class()
        return clazz().POST() 

class DateListHandler:

    type_order_dict = {
        "group"   :  0,
        "gallery" : 10,
        "list"    : 20,
        "table"   : 30,
        "csv"     : 30,
        "md"      : 90,
    }

    def sort_notes(self, notes):
        notes.sort(key = lambda x: self.type_order_dict.get(x.type, 100))

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
        show_back = xutils.get_argument("show_back", "")

        xmanager.add_visit_log(user_name, "/note/date")
        
        date  = xutils.get_argument("date", time.strftime("%Y-%m"))
        parts = date.split("-")
        if len(parts) == 2:
            year = int(parts[0])
            month = int(parts[1])
        else:
            year = int(parts[0])
            month = dateutil.get_current_month()

        notes = []
        # 待办任务
        notes.append(MSG_DAO.get_message_tag(user_name, "task", priority = 2))
        notes.append(MSG_DAO.get_message_tag(user_name, "log",  priority = 2))
        notes.append(NoteLink("我的人生", "/note/view?skey=my_life", priority = 2))
        notes.append(NoteLink("我的年报:%s" % year, "/note/view?skey=year_%s" % year, 
            priority = 2))
        notes.append(NoteLink("我的月报:%s" % date, "/note/view?skey=month_%s" % date, 
            priority = 2))

        notes_new = NOTE_DAO.list_by_date("ctime", user_name, date, orderby = "ctime_desc")
        for note in notes_new:
            note.badge_info = dateutil.format_date(note.ctime)


        notes = notes + notes_new
        notes_by_date = [("置顶", notes)]
        # notes_by_date = NOTE_DAO.assemble_notes_by_date(notes)

        return xtemplate.render("note/page/list_by_date.html", 
            html_title    = T("我的笔记"),
            date          = date,
            year          = year,
            month         = month,
            notes_by_date = notes_by_date,
            show_back     = show_back,
            search_type   = "default")


xutils.register_func("url:/note/group", GroupListHandler)
xutils.register_func("url:/note/tools", NotePluginHandler)
xutils.register_func("url:/note/date",  DateListHandler)
xutils.register_func("url:/note/all", AllNoteListHandler)
xutils.register_func("note.count_smart_group", count_smart_group)
xutils.register_func("note.list_smart_group", list_smart_group)


@xmanager.listen("sys.reload")
def on_reload(ctx):
    list_smart_group("admin")

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
    r"/note/public"         , ShareListHandler,
    r"/note/document"       , DocumentListHandler,
    r"/note/gallery"        , GalleryListHandler,
    r"/note/list"           , CheckListHandler,
    r"/note/table"          , TableListHandler,
    r"/note/removed"        , RemovedListHandler,
    r"/note/sticky"         , StickyListHandler,
    r"/note/log"            , LogListHandler,
    r"/note/all"            , AllNoteListHandler,
    r"/note/html"           , HtmlListHandler,
    r"/note/form"           , FormListHandler,
    r"/note/date"           , DateListHandler,
    r"/note/share_to_me"    , ShareToMeListHandler,

    r"/note/text"           , TextListHandler,
    r"/note/tools"          , NotePluginHandler,
    r"/note/types"          , NotePluginHandler,
    r"/note/index"          , NoteIndexHandler,
)

