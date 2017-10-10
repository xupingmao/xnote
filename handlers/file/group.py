# encoding=utf-8
import math
import web
import xutils
import xtemplate
import xtables
import xauth

from . import dao
from xutils import Storage

class PathNode:

    def __init__(self, name, url):
        self.name = name
        self.url = url

class handler:

    @xauth.login_required()
    def GET(self):
        return xtemplate.render("file/view.html",
            file_type="group",
            pseudo_groups=True,
            files=dao.get_category(xauth.get_current_name()))

    def POST(self):
        pass

class Ungrouped:

    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        db = xtables.get_file_table()

        sql = "SELECT a.* FROM file a LEFT JOIN file b ON a.parent_id = b.id WHERE a.is_deleted = 0 AND a.type != 'group' AND (b.id is null OR b.type != 'group') LIMIT ?, ?"
        files = db.execute(sql, ((page-1)*10, 10))
        
        count_sql = "SELECT COUNT(1) AS amount FROM file a LEFT JOIN file b ON a.parent_id = b.id WHERE a.is_deleted = 0 AND a.type != 'group' AND (b.id is null OR b.type != 'group')"
        amount = db.execute(count_sql)[0].amount

        return xtemplate.render("file/view.html",
            pathlist=[PathNode("未分类", "/file/group/ungrouped")],
            file_type="group",
            files = files,
            page = page,
            page_max = math.ceil(amount / 10),
            page_url="/file/group/ungrouped?page=")

class MoveHandler:
    
    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id", "", type=int)
        parent_id = xutils.get_argument("parent_id", "", type=int)
        db = xtables.get_file_table()
        db.update(parent_id=parent_id, where=dict(id=id))
        return dict(code="success")

    def POST(self):
        return self.GET()
        
class ListHandler:

    def GET(self):
        id = xutils.get_argument("id", "", type=int)
        sql = "SELECT id, name FROM file WHERE type = 'group' AND is_deleted = 0 ORDER BY name DESC LIMIT 200"
        data = xtables.get_file_table().query(sql)
        web.header("Content-Type", "text/html; charset=utf-8")
        return xtemplate.render("file/group_list.html", id=id, filelist=data)

class RemovedHandler:

    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        db = xtables.get_file_table()
        files = db.select(where="is_deleted=1", order="sctime DESC", offset=(page-1)*10, limit=10)
        amount = db.count(where="is_deleted=1")

        return xtemplate.render("file/view.html",
            pathlist=[PathNode("回收站", "/file/group/removed")],
            file_type="group",
            files = files,
            page = page,
            page_max = math.ceil(amount / 10),
            page_url="/file/group/removed?page=")

xurls = (
    r"/file/group", handler,
    r"/file/group/ungrouped", Ungrouped,
    r"/file/group/removed", RemovedHandler,
    r"/file/group/list", ListHandler,
    r"/file/group/move", MoveHandler,
)

