# encoding=utf-8
# @since 2016/12
# @modified 2022/04/22 23:30:02
import math
import time
import json
import logging
try:
    import cProfile as profile
except ImportError:
    import profile
from .dao_book import SmartGroupService

import web
import xutils
from xnote.core import xtemplate
from xnote.core import xauth
from xnote.core import xconfig
from xnote.core import xmanager
from xutils import Storage
from xutils import dateutil, fsutil
from xnote.core.xtemplate import T
from .dao_category import list_category, get_category_by_code
from . import dao_tag
from . import dao
from . import dao_book
from . import dao_share
from . import dao_log
from .dao_api import NoteDao
import handlers.note.dao as note_dao
import handlers.message.dao as msg_dao

VIEW_TPL = "note/page/view.html"
TYPES_NAME = "笔记索引"
NOTE_DAO = xutils.DAO("note")
MSG_DAO = xutils.DAO("message")
PLUGIN = xutils.Module("plugin")


class PathNode(Storage):

    def __init__(self, name, url, type="note"):
        self.name = name
        self.url = url
        self.type = type
        self.priority = 0
        self.icon = type


class GroupLink(Storage):
    """笔记本的类型"""

    def __init__(self, name, url, size=None, type="group"):
        self.type = type
        self.priority = 0
        self.name = name
        self.url = url
        self.size = size
        self.mtime = ""
        self.ctime = ""
        self.show_next = True
        self.icon = "fa-folder orange"


class SystemLink(GroupLink):
    """系统列表项"""

    def __init__(self, name, url, size=None):
        GroupLink.__init__(self, name, url, size, "system")
        self.icon = "icon-folder-system"


class NoteLink:
    def __init__(self, name, url, icon="fa-cube", size=None, roles=None, category="000", priority=0):
        self.type = "link"
        self.name = T(name)
        self.url = url
        self.icon = icon
        self.size = size
        self.priority = priority
        self.ctime = ""
        self.hide = False
        self.show_next = True
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
        NoteLink.__init__(self, "词典", "/note/dict",  "icon-dict", size=size)
        self.hide = xconfig.HIDE_DICT_ENTRY


class NoteCard:

    def __init__(self, title, rows):
        self.title = title
        self.rows = rows


class RecentGroup:

    def __init__(self, user_name):
        self.name = u"最近"
        self.size = None
        self.url = "/note/recent?orderby=create"
        self.icon = "fa-history"
        self.priority = 0
        self.show_next = True
        self.is_deleted = 0


def type_node_path(name, url):
    parent = PathNode(TYPES_NAME, "/note/types")
    return [parent, GroupLink(T(name), url)]


class DefaultListHandler:

    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument("page", 1, type=int)

        assert isinstance(page, int)

        user_name = xauth.get_current_name()
        pagesize = xconfig.PAGE_SIZE
        offset = (page-1) * pagesize
        files = note_dao.list_default_notes(user_name, offset, pagesize)
        amount = note_dao.count_by_parent(user_name, 0)

        return xtemplate.render("note/page/note_default.html",
                                notes=files,
                                page=page,
                                page_max=math.ceil(amount / pagesize),
                                page_url="/note/default?page=")


class ShareListHandler:

    share_type = "public"
    title = T("公开分享")

    def list_notes(self, user_name, offset, limit):
        orderby = xutils.get_argument_str("tab", "ctime_desc")
        notes = note_dao.list_public(offset, limit, orderby)
        return notes

    def count_notes(self, user_name):
        return note_dao.count_public()

    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        tab = xutils.get_argument("tab", "")
        assert isinstance(page, int)

        user_name = xauth.current_name_str()
        limit = xconfig.PAGE_SIZE
        offset = (page-1) * limit

        files = self.list_notes(user_name, offset, limit)
        amount = self.count_notes(user_name)

        xmanager.add_visit_log(user_name, "/note/%s" % self.share_type)
        page_url = "/note/{share_type}?tab={tab}&page=".format(
            share_type=self.share_type, tab=tab)

        return xtemplate.render("note/page/note_share.html",
                                title=self.title,
                                notes=files,
                                page=page,
                                page_max=math.ceil(amount / limit),
                                page_url=page_url)


class PublicListHandler(ShareListHandler):
    pass


class ShareToMeListHandler(ShareListHandler):

    share_type = "share_to_me"
    title = T("分享给我")

    def count_notes(self, user_name):
        return dao_share.count_share_to(user_name)

    def list_notes(self, user_name, offset, limit):
        return dao_share.list_share_to(user_name, offset, limit)


class GroupListHandler:

    def load_category(self, kw, user_name):
        kw.category_list = list(
            filter(lambda x: x.group_count != 0, list_category(user_name)))

    def load_group_list(self, user_name, status, kw):
        parent_id = xutils.get_argument_int("parent_id")

        if status in ("active", "archived"):
            query_root = (status == "active")
            notes = dao.list_group_v2(user_name,
                                   status=status,
                                   orderby="default",
                                   parent_id=parent_id,
                                   query_root=query_root,
                                   tags=kw.q_tags)
        else:
            notes = SmartGroupService.list_smart_group(user_name)

        if status == "active":
            group = note_dao.get_virtual_group(user_name, "ungrouped")
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
            notes.sort(key=lambda x: x.name, reverse=True)

        if orderby == "name_asc":
            notes.sort(key=lambda x: x.name)

        if orderby == "hot_desc":
            for note in notes:
                note.hot_index = note.hot_index or 0
                note.badge_info = "热度(%s)" % note.hot_index
            notes.sort(key=lambda x: x.hot_index, reverse=True)

        if orderby == "size_desc":
            for note in notes:
                note.badge_info = note.children_count

            notes.sort(key=lambda x: x.children_count or 0, reverse=True)

        if orderby == "ctime_desc":
            for note in notes:
                note.ctime = note.ctime or ""
                note.badge_info = note.create_date
            notes.sort(key=lambda x: x.ctime, reverse=True)

        notes.sort(key=lambda x: x.priority, reverse=True)

    def GET(self):
        flag = xutils.get_argument_bool("profile")
        if flag:
            p = profile.Profile()
            r = [0]
            stats = p.runctx("r[0] = self.do_get()", globals(), locals())
            # 排序字段 stdname/calls/time/cumulative
            stats.print_stats(sort="cumulative")
            return r[0]
        else:
            return self.do_get()

    @xauth.login_required()
    def do_get(self):
        user_name = xauth.current_name()
        assert isinstance(user_name, str)

        orderby_default = xconfig.get_user_config(
            user_name, "group_list_order_by", "name_asc")
        logging.debug("orderby_default:%s", orderby_default)

        category = xutils.get_argument("note_category", "all")
        tab = xutils.get_argument("tab", "active")
        orderby = xutils.get_argument("orderby", orderby_default)

        show_back = xutils.get_argument("show_back", type=bool)
        q_tag_name = xutils.get_argument("tag_name", "")
        q_tags = []
        if q_tag_name != "":
            q_tags = [q_tag_name]

        xmanager.add_visit_log(user_name, "/note/group")

        if orderby != orderby_default:
            xconfig.update_user_config(
                user_name, "group_list_order_by", orderby)

        root = note_dao.get_root()
        kw = Storage()
        kw.tab = tab
        kw.orderby = orderby
        kw.title = T("我的笔记本")
        kw.note_category = category
        kw.category_info = get_category_by_code(user_name, category)
        kw.q_tags = q_tags

        notes = self.load_group_list(user_name, tab, kw)

        kw.file = root
        kw.groups = notes
        kw.parent_id = 0
        kw.show_back = show_back
        kw.show_sort = (tab != "smart")
        kw.archived_count = dao.count_group(user_name, status="archived")
        kw.active_count = dao.count_group(user_name, status="active", query_root=True)
        kw.smart_count = SmartGroupService.count_smart_group()
        kw.tag_meta_list = dao_tag.list_tag_meta(user_name, tag_type="group")

        self.handle_badge_info(notes, tab=tab)
        self.sort_notes(notes, kw)

        if tab == "smart":
            kw.show_note_types = False

        return xtemplate.render("note/page/group_list.html", **kw)


class GroupManageHandler:

    def handle_root(self, kw):
        page = xutils.get_argument_int("page", 1)
        orderby = xutils.get_argument_str("orderby", "default")
        category_code = xutils.get_argument("note_category", "all")
        q_key = xutils.get_argument("key", "")
        q_tags_str = xutils.get_argument_str("tags", "[]")

        q_tags = json.loads(q_tags_str)

        assert page > 0
        limit = 1000
        offset = (page-1) * limit

        user_name = kw.user_name
        user_id = kw.get("user_id", 0)
        parent_note = note_dao.get_root()

        list_group_kw = Storage()
        list_group_kw.tags = q_tags
        list_group_kw.search_name = q_key
        list_group_kw.count_total = True
        list_group_kw.category = category_code

        notes, total = note_dao.list_group_with_count(creator_id=user_id, orderby=orderby, offset=offset,
                                           limit=limit, **list_group_kw)
        
        kw.parent_note = parent_note
        kw.notes = notes
        kw.page_totalsize = total
        kw.page_size = limit
        kw.page_url = "?note_category={category}&orderby={orderby}&page=".format(
            category=category_code, orderby=orderby)
        kw.template = "note/page/batch/group_manage.html"
        kw.category_list = list_category(user_name)
        kw.q_tags = q_tags
        kw.q_key = q_key
        kw.search_type = "group_manage"

        cat_info = get_category_by_code(user_name, category_code)
        if cat_info != None:
            kw.category_code = cat_info.code
            kw.category_name = cat_info.name
        else:
            kw.category_code = "unknown"
            kw.category_name = "未知"

        kw.show_category_edit = (category_code != "all")
        kw.note_tags = dao_tag.batch_get_tags_by_notes(kw.notes)

    @xauth.login_required()
    def GET(self):
        parent_id = xutils.get_argument("parent_id", "0")
        user_info = xauth.current_user()
        assert user_info != None

        xmanager.add_visit_log(user_info.name, "/note/group_list/edit")
        kw = Storage(user_name=user_info.name, parent_id=parent_id, user_id=user_info.id)

        self.handle_root(kw)
        kw.current = Storage(url="#", name="整理")
        return xtemplate.render(kw.template, **kw)


def load_note_index(user_name):
    msg_stat = msg_dao.get_message_stat(user_name)
    note_stat = note_dao.get_note_stat(user_name)

    return [
        NoteCard("分类", [
            NoteLink("任务", "/message?tag=task",
                     "fa-calendar-check-o", size=msg_stat.task_count),
            NoteLink("备忘", "/message?tag=log",
                     "fa-sticky-note", size=msg_stat.log_count),
            NoteLink("项目", "/note/group", "fa-folder",
                     size=note_stat.group_count),
            NoteLink("文档", "/note/document", "fa-file-text",
                     size=note_stat.doc_count),
            NoteLink("相册", "/note/gallery", "fa-image",
                     size=note_stat.gallery_count),
            NoteLink("清单", "/note/list", "fa-list", size=note_stat.list_count),
            NoteLink("表格", "/note/table", "fa-table",
                     size=note_stat.table_count),
            NoteLink("日志", "/note/log", "fa-file-text",
                     size=note_stat.log_count),
            DictEntryLink(size=note_stat.dict_count),
            NoteLink("插件", "/plugins_list", "fa-th-large",
                     size=len(xconfig.PLUGINS_DICT), roles=["admin"]),
        ]),

        NoteCard(u"工具", [
            NoteLink("置顶笔记", "/note/sticky", "fa-thumb-tack",
                     size=note_stat.sticky_count),
            NoteLink("搜索历史", "/search", "fa-search", size=None),
            NoteLink("导入笔记", "/note/html_importer", "fa-internet-explorer"),
            NoteLink("时间视图", "/note/date", "fa-calendar"),
            NoteLink("数据统计", "/note/stat", "fa-bar-chart"),
            NoteLink("上传管理", "/fs_upload", "fa-upload"),
            NoteLink("回收站", "/note/removed", "fa-trash",
                     size=note_stat.removed_count),
        ])
    ]


def load_category(user_name, include_system=False):
    data = note_dao.list_group_v2(user_name, orderby="name")
    sticky_groups = list(filter(lambda x: x.priority !=
                         None and x.priority > 0, data))
    archived_groups = list(filter(lambda x: x.archived == True, data))
    normal_groups = list(
        filter(lambda x: x not in sticky_groups and x not in archived_groups, data))
    groups_tuple = [
        ("置顶", sticky_groups),
        ("普通", normal_groups),
        ("归档", archived_groups)
    ]

    if include_system:
        system_folders = [
            NoteLink("笔记", "/note/add", "fa-file-text-o"),
            NoteLink("相册", "/note/add?type=gallery", "fa-photo"),
            NoteLink("表格", "/note/add?type=csv", "fa-table"),
            NoteLink("分组", "/note/add?type=group", "fa-folder")
        ]

        default_book_count = note_dao.count_by_parent(user_name, 0)
        if default_book_count > 0:
            sticky_groups.insert(0, SystemLink(
                "默认分组", "/note/default", default_book_count))
        sticky_groups.insert(0, NoteLink(
            "时光轴", "/note/tools/timeline", "cube"))

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
        view = xutils.get_argument("view", "")
        parent_id = xutils.get_argument("parent_id", "0")
        q_parent_id = None

        groups_tuple = load_category(xauth.current_name())
        web.header("Content-Type", "text/html; charset=utf-8")

        template = "note/component/group_select.html"
        if view == "tree":
            template = "note/component/group_select_tree.html"
            q_parent_id = parent_id
        else:
            # view == flat
            q_parent_id = None

        files = note_dao.list_group(
            user_name, orderby="default", parent_id=q_parent_id)

        parent = note_dao.get_by_id_creator(parent_id, user_name)
        kw = Storage()
        kw.id = id
        kw.groups_tuple = groups_tuple
        kw.callback = callback
        kw.parent_id = parent_id
        kw.parent = parent
        kw.files = files
        return xtemplate.render(template, **kw)

class BaseListHandler:

    note_type = "gallery"
    title = "相册"
    orderby = "ctime desc"
    create_type = ""
    create_text = T("创建笔记")
    date_type = "cdate"
    show_ext_info = True

    def count_notes(self, user_name):
        return note_dao.count_by_type(user_name, self.note_type)

    def list_notes(self, user_name, offset, limit):
        return note_dao.list_by_type(user_name, self.note_type, offset, limit, self.orderby)

    def map_notes(self, notes):
        for note in notes:
            note.badge_info = dateutil.format_date(note.ctime)

        return notes
    
    def get_type_list(self):
        return [
            Storage(url="/note/all", name="全部", tag_code="all"),
            Storage(url="/note/all?type=md", name="文档", tag_code="md"),
            Storage(url="/note/all?type=gallery", name="相册", tag_code="gallery"),
            Storage(url="/note/all?type=list", name="清单", tag_code="list"),
            Storage(url="/note/all?type=table", name="表格", tag_code="table"),
        ]

    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        user_name = xauth.current_name()

        assert isinstance(page, int)

        limit = xconfig.PAGE_SIZE
        offset = (page-1)*limit

        self.note_type = xutils.get_argument_str("type", self.note_type)
        assert isinstance(self.note_type, str)

        amount = self.count_notes(user_name)
        notes = self.list_notes(user_name, offset, limit)
        notes = self.map_notes(notes)

        kw = Storage()
        kw.show_ext_info = self.show_ext_info
        kw.show_pagination = True
        kw.page = page
        kw.page_max = math.ceil(amount / xconfig.PAGE_SIZE)
        kw.page_url = "/note/%s?page=" % self.note_type
        kw.notes = notes
        kw.group_type = self.note_type
        kw.note_type = self.note_type
        kw.title = self.title
        kw.date_type = self.date_type
        kw.type_list = self.get_type_list()
        kw.show_path = False
        kw.file_type = "group"

        # 上级菜单
        parent = PathNode(T("根目录"), "/note/group")
        kw.pathlist = [parent, PathNode(self.title, "/note/" + self.note_type)]
        
        return xtemplate.render("note/page/note_list.html",
                                show_group_option=False,
                                create_text=self.create_text,
                                create_type=self.create_type,
                                **kw)


class TextListHandler(BaseListHandler):

    note_type = "text"
    title = "文本"


class AddressBookListHandler(BaseListHandler):

    note_type = "address"
    title = "通讯录"


class DocumentListHandler(BaseListHandler):

    note_type = "md"
    create_type = "md"
    create_text = T("创建文档")
    title = "我的文档"


class GalleryListHandler(BaseListHandler):

    note_type = "gallery"
    create_type = "gallery"
    create_text = "创建相册"
    title = "我的相册"


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
    title = T("回收站")

    def count_notes(self, user_name):
        return note_dao.count_removed(user_name)

    def list_notes(self, user_name, offset, limit):
        return note_dao.list_removed(user_name, offset, limit, self.orderby)

    def map_notes(self, notes):
        for note in notes:
            note.badge_info = dateutil.format_date(note.dtime)
        return notes


class StickyListHandler(BaseListHandler):

    note_type = "sticky"
    title = T("我的置顶")

    def count_notes(self, user_name):
        note_stat = note_dao.get_note_stat(user_name)
        if note_stat:
            return note_stat.sticky_count
        else:
            return 0

    def list_notes(self, user_name, offset, limit):
        return note_dao.list_sticky(user_name, offset, limit)


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
        note_stat = note_dao.get_note_stat(user_name)
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
        return dao_log.count_visit_log(user_name)

    def list_notes(self, creator, offset, limit, orderby):
        if orderby == "all":
            return dao_log.list_recent_events(creator, offset, limit)
        elif orderby == "view":
            return dao_log.list_recent_viewed(creator, offset, limit)
        elif orderby == "create":
            return dao_log.list_recent_created(creator, offset, limit)
        elif orderby == "myhot":
            return dao_log.list_hot(creator, offset, limit)

        # 最近更新的
        notes = dao_log.list_recent_edit(creator, offset, limit)
        for note in notes:
            note.badge_info = dateutil.format_date(note.mtime, "/")
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

    def GET(self, show_notice=True):
        if not xauth.has_login():
            raise web.seeother("/note/public")
        if xutils.sqlite3 is None:
            raise web.seeother("/fs_list")

        page = xutils.get_argument("page", 1, type=int)
        pagesize = xutils.get_argument("pagesize", xconfig.PAGE_SIZE, type=int)
        orderby = xutils.get_argument("orderby", "create")

        assert isinstance(page, int)
        assert isinstance(pagesize, int)

        page = max(1, page)
        offset = max(0, (page-1) * pagesize)
        limit = pagesize
        dir_type = "recent_edit"
        creator = xauth.current_name_str()

        xmanager.add_visit_log(creator, "/note/recent?orderby=%s" % orderby)

        html_title = self.get_html_title(orderby)
        files = self.list_notes(creator, offset, limit, orderby)
        count = self.count_note(creator, orderby)

        kw = Storage()
        kw.pathlist = type_node_path(html_title, "")
        kw.html_title = html_title
        kw.file_type = "group"
        kw.dir_type = dir_type
        kw.search_type = "note"
        kw.files = files
        kw.show_aside = False
        kw.show_side = False
        kw.page = page
        kw.show_next = False
        kw.page_max = math.ceil(count/xconfig.PAGE_SIZE)
        kw.page_url = "/note/recent?orderby=%s&page=" % orderby
        kw.sticky_position = "right"

        return xtemplate.render("note/page/note_recent.html", **kw)


class ArchivedHandler:

    @xauth.login_required()
    def GET(self):
        raise web.found("/note/group?tab=archived")


class ManagementHandler:
    """批量管理处理器"""

    def handle_group(self, kw):
        q_tags_str = xutils.get_argument_str("tags", "[]")
        q_tags = json.loads(q_tags_str)

        parent_id = kw.parent_id
        user_name = kw.user_name

        parent_note = NoteDao.get_by_id(parent_id)
        if parent_note == None:
            raise web.notfound()

        notes = note_dao.list_by_parent(user_name, parent_id,
                                        offset=0, limit=200, 
                                        orderby=parent_note.orderby, tags=q_tags)

        parent = Storage(url="/note/%s" % parent_id,
                         name=parent_note.name)

        dao_tag.batch_get_tags_by_notes(notes)
        kw.parent_note = parent_note
        kw.parent = parent
        kw.notes = notes

    def handle_default(self, kw):
        user_name = kw.user_name
        parent_note = note_dao.get_default_group()
        notes = note_dao.list_default_notes(user_name)

        kw.parent_note = parent_note
        kw.notes = notes

    @xauth.login_required()
    def GET(self):
        parent_id = xutils.get_argument("parent_id", "0")
        user_name = xauth.current_name_str()

        xmanager.add_visit_log(user_name, "/note/manage")

        kw = Storage(user_name=user_name, parent_id=parent_id)
        kw.template = "note/page/batch/note_manage.html"

        if parent_id == "0" or parent_id is None:
            raise web.found("/note/group/manage")
        elif parent_id == "default":
            self.handle_default(kw)
        else:
            self.handle_group(kw)

        parent_note = kw.parent_note
        notes = kw.notes

        if parent_note is None:
            raise web.seeother("/unauthorized")

        if parent_note.type == "gallery":
            fpath = note_dao.get_gallery_path(parent_note)
            pathlist = fsutil.listdir_abs(fpath, False)
            return xtemplate.render("note/page/batch/gallery_manage.html",
                                    note=parent_note,
                                    dirname=fpath,
                                    pathlist=pathlist)

        current = Storage(url="#", name="整理")
        return xtemplate.render(kw.template,
                                pathlist=note_dao.list_path(parent_note),
                                files=notes,
                                show_path=True,
                                current=current, **kw)


class NoteIndexHandler:

    def find_class(self):
        user_name = xauth.current_name()
        home_path = xconfig.get_user_config(user_name, "HOME_PATH")
        if xutils.is_mobile_client():
            home_path = xconfig.get_user_config(user_name, "HOME_PATH_MOBILE")
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
        user_name = xauth.current_name_str()
        show_back = xutils.get_argument("show_back", "")

        xmanager.add_visit_log(user_name, "/note/date")

        date = xutils.get_argument_str("date", time.strftime("%Y-%m"))
        parts = date.split("-")
        if len(parts) == 2:
            year = int(parts[0])
            month = int(parts[1])
        else:
            year = int(parts[0])
            month = dateutil.get_current_month()

        notes = []
        # 待办任务
        notes.append(msg_dao.get_message_tag(user_name, "task", priority=2))
        notes.append(msg_dao.get_message_tag(user_name, "log",  priority=2))
        notes_new = note_dao.list_by_date(
            "ctime", user_name, date, orderby="ctime desc")
        for note in notes_new:
            note.badge_info = dateutil.format_date(note.ctime)

        notes = notes + notes_new
        notes_by_date = [("置顶", notes)]
        # notes_by_date = NOTE_DAO.assemble_notes_by_date(notes)

        return xtemplate.render("note/page/list_by_date.html",
                                html_title=T("我的笔记"),
                                date=date,
                                year=year,
                                month=month,
                                notes_by_date=notes_by_date,
                                show_back=show_back,
                                search_type="default")


xutils.register_func("url:/note/group", GroupListHandler)
xutils.register_func("url:/note/tools", NotePluginHandler)
xutils.register_func("url:/note/date",  DateListHandler)
xutils.register_func("url:/note/all", AllNoteListHandler)

xurls = (
    r"/note/group", GroupListHandler,
    r"/note/group_list", GroupListHandler,
    r"/note/group/manage", GroupManageHandler,
    r"/note/books", GroupListHandler,
    r"/note/default", DefaultListHandler,
    r"/note/ungrouped", DefaultListHandler,
    r"/note/archived", ArchivedHandler,
    r"/note/recent_edit", RecentHandler,
    r"/note/recent", RecentHandler,
    r"/note/recent_(created)", RecentHandler,
    r"/note/recent_(viewed)", RecentHandler,
    r"/note/group/select", GroupSelectHandler,
    r"/note/management", ManagementHandler,
    r"/note/manage", ManagementHandler,
    r"/note/public", ShareListHandler,
    r"/note/document", DocumentListHandler,
    r"/note/md", DocumentListHandler,
    r"/note/gallery", GalleryListHandler,
    r"/note/list", CheckListHandler,
    r"/note/table", TableListHandler,
    r"/note/removed", RemovedListHandler,
    r"/note/sticky", StickyListHandler,
    r"/note/log", LogListHandler,
    r"/note/all", AllNoteListHandler,
    r"/note/html", HtmlListHandler,
    r"/note/form", FormListHandler,
    r"/note/date", DateListHandler,
    r"/note/share_to_me", ShareToMeListHandler,

    r"/note/text", TextListHandler,
    r"/note/tools", NotePluginHandler,
    r"/note/types", NotePluginHandler,
    r"/note/index", NoteIndexHandler,
)
