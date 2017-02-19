# encoding=utf-8

import web
import xtemplate
import FileDB

class handler:

    def GET(self):
        return xtemplate.render("file-list.html",
            files=FileDB.get_category())

    def POST(self):
        pass