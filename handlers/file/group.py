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

class FileListHandler:

    @xauth.login_required()
    def GET(self):
        return xtemplate.render("file/view.html",
            file_type="group",
            pseudo_groups=True,
            show_search_div=True,
            files=dao.get_category(xauth.get_current_name()))

    def POST(self):
        pass

class Ungrouped:

    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        db = xtables.get_file_table()
        pagesize = xconfig.PAGE_SIZE

        sql = "SELECT a.* FROM file a LEFT JOIN file b ON a.parent_id = b.id WHERE a.is_deleted = 0 AND a.type != 'group' AND (b.id is null OR b.type != 'group') ORDER BY smtime DESC LIMIT %s,%s"
        files = db.query(sql % ((page-1)*pagesize, pagesize))
        
        count_sql = "SELECT COUNT(1) AS amount FROM file a LEFT JOIN file b ON a.parent_id = b.id WHERE a.is_deleted = 0 AND a.type != 'group' AND (b.id is null OR b.type != 'group')"
        amount = db.count(sql = count_sql)

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
        db.update(parent_id=parent_id, where=dict(id=id))
        return dict(code="success")

    def POST(self):
        return self.GET()
        
class GroupListHandler:

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

class RecentCreatedHandler:

    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        page = max(1, page)
        db = xtables.get_file_table()
        where = "is_deleted=0 AND creator=%r" % xauth.get_current_name()
        files = db.select(where=where, order="sctime DESC", offset=page*PAGE_SIZE,limit=PAGE_SIZE)
        count = db.count(where=where)
        return xtemplate.render("file/view.html", 
            pathlist = [Storage(name="最近创建", url="/file/group/recent_created")],
            file_type = "group",
            files = files,
            page = page, 
            page_max = math.ceil(count/PAGE_SIZE), 
            page_url="/file/recent_edit?page=")

class BookmarkHandler:
    
    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument("page", 1, type=int)
        page = max(1, page)
        db = xtables.get_file_table()
        where = "is_deleted=0 AND is_marked=1 AND creator=%r" % xauth.get_current_name()
        files = db.select(where=where, order="smtime DESC", offset=(page-1)*PAGE_SIZE,limit=PAGE_SIZE)
        count = db.count(where=where)
        return xtemplate.render("file/view.html", 
            pathlist = [Storage(name="收藏", url="/file/group/bookmark")],
            file_type = "group",
            files = files,
            page = page, 
            page_max = math.ceil(count/PAGE_SIZE), 
            page_url="/file/group/bookmark?page=")


class MemoHandler:

    @xauth.login_required("admin")
    def GET(self):
        db = xtables.get_schedule_table()
        # files = db.select()
        files = xmanager.get_task_list()
        def set_display_name(file):
            file.display_name = file.name if file.name != "" else file.url
            return file
        files = list(map(set_display_name, files))
        return xtemplate.render("file/view.html", 
            pathlist = [PathNode("备忘录", "/file/group/memo")],
            file_type = "memo",
            files = files)

xurls = (
    r"/file/group", FileListHandler,
    r"/file/group/ungrouped", Ungrouped,
    r"/file/group/removed", RemovedHandler,
    r"/file/group/list", GroupListHandler,
    r"/file/group/move", MoveHandler,
    r"/file/group/bookmark", BookmarkHandler,
    r"/file/group/recent_created", RecentCreatedHandler,
    r"/file/group/memo", MemoHandler,
)

