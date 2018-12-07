# encoding=utf-8
# @since 2016/12
# @modified 2018/12/08 02:22:32
import math
import web
import xutils
import xtemplate
import xtables
import xauth
import xconfig
import xmanager
from xutils import Storage
from xutils import cacheutil
from xutils.dateutil import Timer

# 兼容旧代码
config = xconfig
PAGE_SIZE = xconfig.PAGE_SIZE

VIEW_TPL = "note/view.html"

def update_children_count(parent_id, db=None):
    if parent_id is None or parent_id == "":
        return
    group_count = db.count(where="parent_id=$parent_id AND is_deleted=0", vars=dict(parent_id=parent_id))
    db.update(size=group_count, where=dict(id=parent_id))

class PathNode:

    def __init__(self, name, url):
        self.name = name
        self.url = url

class Ungrouped:

    @xauth.login_required()
    def GET(self):
        page           = xutils.get_argument("page", 1, type=int)
        db             = xtables.get_file_table()
        user_name      = xauth.get_current_name()
        pagesize       = xconfig.PAGE_SIZE
        vars           = dict()
        vars["name"]   = user_name
        vars["offset"] = (page-1) * pagesize
        vars["limit"]  = pagesize

        sql = """SELECT a.* FROM file a LEFT JOIN file b ON a.parent_id = b.id 
            WHERE a.is_deleted = 0 
                AND a.type != 'group' 
                AND a.creator = $name AND (b.id is null OR b.type != 'group') 
            ORDER BY mtime DESC LIMIT $offset, $limit"""
        files = db.query(sql, vars=vars)
        
        count_sql = """SELECT COUNT(1) AS amount FROM file a LEFT JOIN file b ON a.parent_id = b.id 
            WHERE a.is_deleted = 0 
                AND a.type != 'group' 
                AND a.creator = $name
                AND (b.id is null OR b.type != 'group')"""
        amount = db.count(sql = count_sql, vars = vars)

        return xtemplate.render(VIEW_TPL,
            file_type  = "group",
            pathlist   = [Storage(name="未分类", type="group", url="/file/group/ungrouped")],
            files      = files,
            file       = Storage(name="未分类", type="group"),
            page       = page,
            page_max   = math.ceil(amount / pagesize),
            groups     = xutils.call("note.list_group"),
            show_mdate = True,
            page_url   = "/file/group/ungrouped?page=")

class MoveHandler:
    
    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", "", type=int)
        parent_id = xutils.get_argument("parent_id", "", type=int)
        db = xtables.get_file_table()
        file = db.select_one(where=dict(id=id))
        if file is None:
            return dict(code="fail", message="file not exists")
        db.update(parent_id=parent_id, where=dict(id=id))
        update_children_count(file.parent_id, db=db)
        update_children_count(parent_id, db=db)
        return dict(code="success")

    def POST(self):
        return self.GET()
        
class GroupListHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", "", type=int)
        data = xutils.call("note.list_group", xauth.get_current_name())
        ungrouped_count = xtables.get_file_table().count(where="creator=$creator AND parent_id=0 AND is_deleted=0 AND type!='group'", 
            vars=dict(creator=xauth.get_current_name()))
        return xtemplate.render(VIEW_TPL,
            ungrouped_count = ungrouped_count,
            file_type       = "group_list",
            pseudo_groups   = True,
            show_search_div = True,
            show_add_group  = True,
            files           = data)

class GroupSelectHandler:
    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", "", type=int)
        filetype = xutils.get_argument("filetype", "")
        data = xutils.call("note.list_group", xauth.get_current_name())
        web.header("Content-Type", "text/html; charset=utf-8")
        return xtemplate.render("note/group_select.html", 
            id=id, filelist=data, file_type="group")



class RemovedHandler:

    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        db = xtables.get_file_table()
        files = db.select(where="is_deleted=1", order="ctime DESC", offset=(page-1)*10, limit=10)
        amount = db.count(where="is_deleted=1")

        return xtemplate.render(VIEW_TPL,
            pathlist  = [PathNode("回收站", "/file/group/removed")],
            file_type = "group",
            files     = files,
            page      = page,
            page_max  = math.ceil(amount / 10),
            page_url  = "/file/group/removed?page=")

class RecentCreatedHandler:

    @xauth.login_required()
    def GET(self):
        page   = xutils.get_argument("page", 1, type=int)
        offset = max(0, (page-1)*PAGE_SIZE)
        db     = xtables.get_file_table()
        where  = "is_deleted=0 AND creator=$creator AND type != 'group'"
        files = db.select(where = where, 
            vars   = dict(creator = xauth.get_current_name()),
            order  = "ctime DESC",
            offset = offset,
            limit  = PAGE_SIZE)
        count = db.count(where = where, 
            vars = dict(creator = xauth.get_current_name()))

        return xtemplate.render("note/view.html",
            html_title = "最近创建",
            file_type  = "group", 
            files      = files, 
            pathlist   = [Storage(name="最近创建", type="group", url="/note/recent_created")],
            groups     = xutils.call("note.list_group"),
            page       = page,
            page_max   = int(math.ceil(count/PAGE_SIZE)),
            page_url   = "/note/recent_created?page=",
            show_aside = True,
            show_cdate = True,
            show_opts  = True)

class RecentEditHandler:
    """show recent modified files"""

    def GET(self):
        if not xauth.has_login():
            raise web.seeother("/note/public")
        if xutils.sqlite3 is None:
            raise web.seeother("/fs_list")
        days     = xutils.get_argument("days", 30, type=int)
        page     = xutils.get_argument("page", 1, type=int)
        pagesize = xutils.get_argument("pagesize", PAGE_SIZE, type=int)
        page     = max(1, page)
        offset   = max(0, (page-1) * pagesize)
        limit    = pagesize

        creator = xauth.get_current_name()
        files   = xutils.call("note.list_recent_edit", None, offset, limit)
        groups  = xutils.call("note.list_group", creator)
        count   = xutils.call("note.count_recent_edit", creator)

        return xtemplate.render("note/view.html", 
            html_title  = "最近更新",
            pathlist    = [Storage(name="最近更新", type="group", url="/file/recent_edit")],
            file_type   = "group",
            files       = files, 
            file        = Storage(name="最近更新", type="group"),
            groups      = groups,
            show_notice = True,
            show_mdate  = True,
            show_groups = True,
            show_aside  = True,
            page        = page, 
            page_max    = math.ceil(count/PAGE_SIZE), 
            page_url    ="/file/recent_edit?page=")


class PublicGroupHandler:

    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        page = max(1, page)
        db = xtables.get_file_table()
        where = "is_deleted=0 AND is_public=1"
        files = db.select(where=where, offset=(page-1)*PAGE_SIZE, limit=PAGE_SIZE, order="ctime DESC")
        count = db.count(where=where)
        return xtemplate.render(VIEW_TPL, 
            show_aside = True,
            pathlist   = [Storage(name="分享笔记", url="/file/group/public")],
            file_type  = "group",
            files      = files,
            page       = page, 
            show_cdate = True,
            groups     = xutils.call("note.list_group"),
            page_max   = math.ceil(count/PAGE_SIZE), 
            page_url   = "/file/group/public?page=")

xurls = (
    r"/file/group"          , GroupListHandler,
    r"/note/group"          , GroupListHandler,
    r"/note/ungrouped"      , Ungrouped,
    r"/file/group/removed"  , RemovedHandler,
    r"/file/group/list"     , GroupListHandler,
    r"/note/group/move"     , MoveHandler,
    r"/file/group/move"     , MoveHandler,
    r"/note/recent_created" , RecentCreatedHandler,
    r"/note/recent_edit"    , RecentEditHandler,
    r"/file/recent_edit"    , RecentEditHandler,
    r"/file/group/public"   , PublicGroupHandler,
    r"/note/public"         , PublicGroupHandler,
    r"/note/group/select"   , GroupSelectHandler
)

