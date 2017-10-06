# encoding=utf-8

import web
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
        db = xtables.get_file_table()
        sql = "SELECT a.* FROM file a LEFT JOIN file b ON a.parent_id = b.id WHERE a.is_deleted = 0 AND a.type != 'group' AND (b.id is null OR b.type != 'group') LIMIT 200"
        files = db.execute(sql)
        return xtemplate.render("file/view.html",
            file_type="group",
            files = files)


xurls = (
    r"/file/group", handler,
    r"/file/group/ungrouped", Ungrouped,
)