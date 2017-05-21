# encoding=utf-8
from handlers.base import *
from handlers.file import dao

class handler(BaseHandler):

    def execute(self):
        self.id = 0
        self.render(
            recentlist=dao.get_recent_visit(7), 
            category=dao.get_category(),
            )

searchable = False

class Home:

    def GET(self):
        # return xtemplate.render("home.html")
        raise web.seeother("/file/recent_edit")

xurls = ("/", Home, "/index", handler)

