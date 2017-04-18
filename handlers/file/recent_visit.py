#coding:utf-8
from handlers.base import *
from . import dao

class handler(BaseHandler):

    __xurl__ = r"/file/recent_visit|/file/recent"
    """show recent modified files"""
    def default_request(self):
        count = self.get_argument("count", 20)
        files = dao.get_recent_visit(count)
        self.render("file-list.html", files = files, key = "")

