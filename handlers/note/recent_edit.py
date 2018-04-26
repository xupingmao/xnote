#coding:utf-8
import math
import xconfig
import xauth
import xutils
import xtables
import xtemplate
from .dao import *
from xutils import Storage

# 兼容旧代码
config = xconfig
PAGE_SIZE = xconfig.PAGE_SIZE

class RecentCreatedHandler:

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

class handler:
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
            pathlist = [],
            file_type = "group",
            files = list(files), 
            file = Storage(name="最近更新", type="group"),
            page = page, 
            page_max = math.ceil(count/PAGE_SIZE), 
            show_mdate = True,
            page_url="/file/recent_edit?page=")

xurls = (
    r"/file/recent_edit", handler
)

