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
            files=dao.get_category(xauth.get_current_name()))

    def POST(self):
        pass
