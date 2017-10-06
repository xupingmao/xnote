# encoding=utf-8
import math
import web
import xutils
import xtemplate
import xtables
import xauth

from . import dao

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
            file_type="group",
            files = files,
            page = page,
            page_max = math.ceil(amount / 10),
            page_url="/file/group/ungrouped?page=")


xurls = (
    r"/file/group", handler,
    r"/file/group/ungrouped", Ungrouped,
)