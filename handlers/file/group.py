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

PAGE_SIZE = xconfig.PAGE_SIZE

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

        return xtemplate.render("file/view.html",
            pathlist=[PathNode("未分类", "/file/group/ungrouped")],
            file_type="group",
            files = files,
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
        data = xtables.get_file_table().query(sql, vars = dict(creator=xauth.get_current_name()))
        if filetype == "xml":
            web.header("Content-Type", "text/html; charset=utf-8")
            return xtemplate.render("file/group_list.html", id=id, filelist=data, file_type="group")
        else:
            return xtemplate.render("file/view.html",
                file_type="group",
                pseudo_groups=True,
                show_search_div = True,
                files=data)

class RemovedHandler:

    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        db = xtables.get_file_table()
        files = db.select(where="is_deleted=1", order="ctime DESC", offset=(page-1)*10, limit=10)
        amount = db.count(where="is_deleted=1")

        return xtemplate.render("file/view.html",
            pathlist=[PathNode("回收站", "/file/group/removed")],
            file_type="group",
            files = files,
            page = page,
            page_max = math.ceil(amount / 10),
            page_url="/file/group/removed?page=")

class RecentCreatedHandler:

    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        page = max(1, page)
        db = xtables.get_file_table()
        where = "is_deleted=0 AND creator=%r" % xauth.get_current_name()
        files = db.select(where=where, order="ctime DESC", offset=page*PAGE_SIZE,limit=PAGE_SIZE)
        count = db.count(where=where)
        return xtemplate.render("file/view.html", 
            pathlist = [Storage(name="最近创建", url="/file/group/recent_created")],
            file_type = "group",
            files = files,
            page = page, 
            page_max = math.ceil(count/PAGE_SIZE), 
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
        return xtemplate.render("file/view.html", 
            pathlist = [Storage(name="收藏", url="/file/group/marked")],
            file_type = "group",
            files = files,
            page = page, 
            page_max = math.ceil(count/PAGE_SIZE), 
            page_url="/file/group/marked?page=")

xurls = (
    r"/file/group", GroupListHandler,
    r"/file/group/ungrouped", Ungrouped,
    r"/file/group/removed", RemovedHandler,
    r"/file/group/list", GroupListHandler,
    r"/file/group/move", MoveHandler,
    r"/file/group/bookmark", MarkedHandler,
    r"/file/group/marked", MarkedHandler,
    r"/file/group/recent_created", RecentCreatedHandler
)

