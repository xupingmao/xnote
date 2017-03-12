# encoding=utf-8
from handlers.base import *
import FileDB

class handler(BaseHandler):

    def execute(self):
        self.id = 0
        self.render(
            recentlist=FileDB.get_recent_visit(7), 
            category=FileDB.get_category(),
            )

searchable = False

class Home:

    def GET(self):
        raise web.seeother("/file/recent_edit")

xurls = ("/", Home, "/index", handler)