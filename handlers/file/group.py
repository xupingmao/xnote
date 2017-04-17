# encoding=utf-8

import web
import xtemplate

from . import dao

class handler:

    def GET(self):
        return xtemplate.render("file-list.html",
            files=dao.get_category())

    def POST(self):
        pass