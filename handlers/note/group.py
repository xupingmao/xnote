# encoding=utf-8
import math
import web
import xutils
import xtemplate
import xtables
import xauth
import xconfig
import xmanager
from . import dao
from xutils import Storage

# 兼容旧代码
config = xconfig
PAGE_SIZE = xconfig.PAGE_SIZE

VIEW_TPL = "note/view.html"

class PathNode:

    def __init__(self, name, url):
        self.name = name
        self.url = url

class Ungrouped:

    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        db = xtables.get_file_table()
        user_name = xauth.get_current_name()
        pagesize = xconfig.PAGE_SIZE

        vars = dict()
        vars["name"] = user_name
        vars["offset"] = (page-1) * pagesize
        vars["limit"] = pagesize

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
            file_type="group",
            files = files,
            file = Storage(name="未分类", type="group"),
            page = page,
            page_max = math.ceil(amount / pagesize),
            page_url="/file/group/ungrouped?page=")

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
        dao.update_children_count(file.parent_id, db=db)
        dao.update_children_count(parent_id, db=db)
        return dict(code="success")

    def POST(self):
        return self.GET()
        
class GroupListHandler:

    def GET(self):
        id = xutils.get_argument("id", "", type=int)
        filetype = xutils.get_argument("filetype", "")
        sql = "SELECT * FROM file WHERE type = 'group' AND is_deleted = 0 AND creator = $creator ORDER BY name LIMIT 1000"
        data = list(xtables.get_file_table().query(sql, vars = dict(creator=xauth.get_current_name())))
        if filetype == "xml":
            web.header("Content-Type", "text/html; charset=utf-8")
            return xtemplate.render("note/group_list.html", id=id, filelist=data, file_type="group")
        else:
            ungrouped_count = xtables.get_file_table().count(where="creator=$creator AND parent_id=0 AND is_deleted=0 AND type!='group'", 
                vars=dict(creator=xauth.get_current_name()))
            return xtemplate.render(VIEW_TPL,
                ungrouped_count = ungrouped_count,
                file_type="group_list",
                pseudo_groups=True,
                show_search_div = True,
                show_add_group = True,
                files=data)

class RemovedHandler:

    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        db = xtables.get_file_table()
        files = db.select(where="is_deleted=1", order="ctime DESC", offset=(page-1)*10, limit=10)
        amount = db.count(where="is_deleted=1")

        return xtemplate.render(VIEW_TPL,
            pathlist=[PathNode("回收站", "/file/group/removed")],
            file_type="group",
            files = files,
            page = page,
            page_max = math.ceil(amount / 10),
            page_url="/file/group/removed?page=")

class RecentCreatedHandler:

    @xauth.login_required()
    def GET(self):
        offset = 0
        db = xtables.get_file_table()
        files = db.select(where="is_deleted=0 AND creator=$name", 
            vars=dict(name=xauth.get_current_name()),
            order="ctime DESC",
            offset=offset,
            limit=PAGE_SIZE)
        return xtemplate.render("note/view.html",
            file_type = "group", 
            files = files, 
            show_date = True,
            show_opts = False)

class RecentEditHandler:
    """show recent modified files"""

    @xauth.login_required()
    def GET(self):
        days = xutils.get_argument("days", 30, type=int)
        page = xutils.get_argument("page", 1, type=int)
        page = max(1, page)

        db = xtables.get_file_table()
        where = "is_deleted = 0 AND (creator = $creator OR is_public = 1)"
        files = db.select(where = where, 
            vars = dict(creator = xauth.get_current_name()),
            order = "mtime DESC",
            offset = (page-1) * PAGE_SIZE,
            limit = PAGE_SIZE)
        count = db.count(where, vars = dict(creator = xauth.get_current_name()))
        return xtemplate.render("note/view.html", 
            pathlist = [Storage(name="最近更新", type="group", url="/file/recent_edit")],
            file_type = "group",
            files = list(files), 
            file = Storage(name="最近更新", type="group"),
            page = page, 
            page_max = math.ceil(count/PAGE_SIZE), 
            show_mdate = True,
            page_url="/file/recent_edit?page=")

class MarkedHandler:
    
    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        page = max(1, page)
        db = xtables.get_file_table()
        vars = dict(creator=xauth.get_current_name())
        where = "is_deleted=0 AND is_marked=1 AND creator=$creator"
        files = db.select(where=where, order="mtime DESC", vars=vars, offset=(page-1)*PAGE_SIZE,limit=PAGE_SIZE)
        count = db.count(where=where, vars=vars)
        return xtemplate.render(VIEW_TPL, 
            pathlist = [Storage(name="收藏", url="/file/group/marked")],
            file_type = "group",
            files = files,
            page = page, 
            page_max = math.ceil(count/PAGE_SIZE), 
            page_url="/file/group/marked?page=")

class PublicGroupHandler:

    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        page = max(1, page)
        db = xtables.get_file_table()
        where = "is_deleted=0 AND is_public=1"
        files = db.select(where=where, offset=(page-1)*PAGE_SIZE, limit=PAGE_SIZE, order="ctime DESC")
        count = db.count(where=where)
        return xtemplate.render(VIEW_TPL, 
            pathlist = [Storage(name="公开", url="/file/group/public")],
            file_type = "group",
            files = files,
            page = page, 
            show_cdate = True,
            page_max = math.ceil(count/PAGE_SIZE), 
            page_url="/file/group/public?page=")

xurls = (
    r"/file/group", GroupListHandler,
    r"/note/group", GroupListHandler,
    r"/file/group/ungrouped", Ungrouped,
    r"/file/group/removed", RemovedHandler,
    r"/file/group/list", GroupListHandler,
    r"/file/group/move", MoveHandler,
    r"/file/group/bookmark", MarkedHandler,
    r"/file/group/marked", MarkedHandler,
    r"/file/group/recent_created", RecentCreatedHandler,
    r"/file/recent_edit", RecentEditHandler,
    r"/file/group/public", PublicGroupHandler
)

