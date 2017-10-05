# encoding=utf-8

import web
import xtemplate
import xtables

from . import dao

class handler:

    def GET(self):
        return xtemplate.render("file/view.html",
            file_type="group",
            files=dao.get_category())

    def POST(self):
        pass

        # 18986556523
