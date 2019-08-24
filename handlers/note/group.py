# encoding=utf-8
# @since 2016/12
# @modified 2019/08/25 00:17:11
import math
import time
import web
import xutils
import xtemplate
import xtables
import xauth
import xconfig
import xmanager
from xutils import Storage
from xutils import cacheutil, dateutil
from xutils.dateutil import Timer
from xtemplate import T

VIEW_TPL = "note/view.html"

class PathNode:

    def __init__(self, name, url):
        self.name = name
        self.url  = url

class GroupItem:
    """笔记本的类型"""

    def __init__(self, name, url):
        self.type     = "group"
        self.priority = 0
        self.name     = name
        self.url      = url
        self.mtime    = dateutil.format_time()

class DefaultListHandler:

    @xauth.login_required()
    def GET(self):
        page      = xutils.get_argument("page", 1, type=int)
        user_name = xauth.get_current_name()
        pagesize  = xconfig.PAGE_SIZE
        offset    = (page-1) * pagesize
        files     = xutils.call("note.list_note", user_name, 0, offset, pagesize)
        amount    = xutils.call("note.count", user_name, 0);
        parent    = PathNode("智能分类", "/note/types")

        return xtemplate.render(VIEW_TPL,
            show_aside = True,
            file_type  = "group",
            pathlist   = [parent, Storage(name="默认分类", type="group", url="/note/default")],
            files      = files,
            file       = Storage(name="默认分类", type="group"),
            page       = page,
            page_max   = math.ceil(amount / pagesize),
            groups     = xutils.call("note.list_group"),
            show_mdate = True,
            page_url   = "/note/default?page=")

class MoveHandler:
    
    @xauth.login_required()
    def GET(self):
        id        = xutils.get_argument("id", "")
        parent_id = xutils.get_argument("parent_id", "")
        file = xutils.call("note.get_by_id", id)
        if file is None:
            return dict(code="fail", message="file not exists")

        xutils.call("note.update", dict(id=id), parent_id = parent_id)
        return dict(code="success")

    def POST(self):
        return self.GET()
        
class GroupListHandler:

    @xauth.login_required()
    def GET(self):
        id   = xutils.get_argument("id", "", type=int)
        data = xutils.call("note.list_group", xauth.current_name())
        return xtemplate.render("note/group_list.html",
            ungrouped_count = 0,
            file_type       = "group_list",
            pseudo_groups   = True,
            show_search_div = True,
            show_add_group  = True,
            show_aside      = True,
            files           = data)

class GroupSelectHandler:
    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", "")
        filetype = xutils.get_argument("filetype", "")
        data = xutils.call("note.list_group", xauth.current_name())
        web.header("Content-Type", "text/html; charset=utf-8")
        return xtemplate.render("note/group_select.html", 
            id=id, filelist=data, file_type="group")



class RemovedHandler:

    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        user_name = xauth.current_name()

        limit  = xconfig.PAGE_SIZE
        offset = (page-1)*limit

        amount = xutils.call("note.count_removed", user_name)
        files  = xutils.call("note.list_removed", user_name, offset, limit)
        parent = PathNode("智能分类", "/note/types")

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

    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        user_name = xauth.current_name()

        limit  = xconfig.PAGE_SIZE
        offset = (page-1)*limit

        amount = xutils.call("note.count_by_type", user_name, self.note_type)
        files  = xutils.call("note.list_by_type",  user_name, self.note_type, offset, limit)

        # 上级菜单
        parent = PathNode("智能分类", "/note/types")
        return xtemplate.render(VIEW_TPL,
            pathlist  = [parent, PathNode(self.title, "/note/" + self.note_type)],
            file_type = "group",
            group_type = self.note_type,
            files     = files,
            page      = page,
            show_aside = True,
            show_mdate = True,
            page_max  = math.ceil(amount / xconfig.PAGE_SIZE),
            page_url  = "/note/%s?page=" % self.note_type)

class GalleryListHandler(BaseListHandler):

    def __init__(self):
        self.note_type = "gallery"
        self.title = "相册"

class TableListHandler(BaseListHandler):

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

class MarkdownListHandler(BaseListHandler):

    def __init__(self):
        self.note_type = "md"
        self.title = "Markdown"

class ListHandler(BaseListHandler):

    def __init__(self):
        self.note_type = "list"
        self.title = "清单"

class TypeListHandler:

    def GET(self):
        page = 1

        limit  = xconfig.PAGE_SIZE
        offset = (page-1)*limit

        files = [
            GroupItem("默认分类", "/note/default"),
            GroupItem("回收站", "/note/removed"),
            GroupItem("公开笔记", "/note/public"),
            GroupItem("最近更新", "/note/recent_edit"),
            GroupItem("最近创建", "/note/recent_created"),
            GroupItem("最近浏览", "/note/recent_viewed"),
            GroupItem("相册", "/note/gallery"),
            GroupItem("表格", "/note/table"),
            GroupItem("通讯录", "/note/addressbook"),
            GroupItem("富文本", "/note/html"),
        ]
        amount = len(files)

        return xtemplate.render(VIEW_TPL,
            pathlist  = [PathNode("智能分类", "/note/types")],
            file_type = "group",
            files     = files,
            show_aside = True,
            show_mdate = True)

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

        creator = xauth.get_current_name()
        if orderby == "viewed":
            html_title = "Recent Viewed"
            files = xutils.call("note.list_recent_viewed", creator, offset, limit)
            time_attr = "atime"
        elif orderby == "created":
            html_title = "Recent Created"
            files = xutils.call("note.list_recent_created", None, offset, limit)
            time_attr = "ctime"
        else:
            html_title = "Recent Updated"
            files = xutils.call("note.list_recent_edit", None, offset, limit)
            time_attr = "mtime"
        
        count   = xutils.call("note.count_user_note", creator)

        return xtemplate.render("note/recent.html", 
            html_title  = html_title,
            file_type   = "group",
            files       = files, 
            show_notice = show_notice,
            show_mdate  = True,
            show_groups = False,
            show_aside  = True,
            page        = page, 
            time_attr   = time_attr,
            page_max    = math.ceil(count/xconfig.PAGE_SIZE), 
            page_url    ="/note/recent_%s?page=" % orderby)


class PublicGroupHandler:

    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        page = max(1, page)
        offset = (page - 1) * xconfig.PAGE_SIZE
        files = xutils.call("note.list_public", offset, xconfig.PAGE_SIZE)
        count = xutils.call("note.count_public")
        return xtemplate.render(VIEW_TPL, 
            show_aside = True,
            pathlist   = [Storage(name="公开笔记", url="/note/public")],
            file_type  = "group",
            files      = files,
            page       = page, 
            show_cdate = True,
            groups     = xutils.call("note.list_group"),
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

        return xtemplate.render("note/list_by_date.html", 
            show_aside = True,
            link_by_month = link_by_month,
            year = int(year),
            month = int(month),
            notes = notes)

class StickyHandler:

    @xauth.login_required()
    def GET(self):
        user  = xauth.current_name()
        files = xutils.call("note.list_sticky", user)
        return xtemplate.render(VIEW_TPL,
            pathlist  = [PathNode("置顶笔记", "/note/sticky")],
            file_type = "group",
            files     = files,
            show_aside = True,
            show_mdate = True)


xurls = (
    r"/note/group"          , GroupListHandler,
    r"/note/group_list"     , GroupListHandler,
    r"/note/books"          , GroupListHandler,
    r"/note/default"        , DefaultListHandler,
    r"/note/ungrouped"      , DefaultListHandler,
    r"/note/public"         , PublicGroupHandler,
    r"/note/removed"        , RemovedHandler,
    r"/note/sticky"         , StickyHandler,
    r"/note/recent_(created)" , RecentHandler,
    r"/note/recent_edit"    , RecentHandler,
    r"/note/recent_(viewed)", RecentHandler,
    r"/note/group/move"     , MoveHandler,
    r"/note/group/select"   , GroupSelectHandler,
    r"/note/date"           , DateHandler,
    r"/note/monthly"        , DateHandler,

    # 笔记分类
    r"/note/gallery"        , GalleryListHandler,
    r"/note/table"          , TableListHandler,
    r"/note/csv"            , TableListHandler,
    r"/note/html"           , HtmlListHandler,
    r"/note/addressbook"    , AddressBookHandler,
    r"/note/md"             , MarkdownListHandler,
    r"/note/list"           , ListHandler,
    r"/note/types"          , TypeListHandler,
    
    r"/file/group/removed"  , RemovedHandler,
    r"/file/group/list"     , GroupListHandler,
    r"/file/group/move"     , MoveHandler,
    r"/file/recent_edit"    , RecentHandler,
)

