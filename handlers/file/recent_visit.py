#coding:utf-8
from handlers.base import *
from FileDB import *

class handler(BaseHandler):

    __xurl__ = r"/file/recent_visit|/file/recent"
    """show recent modified files"""
    def get(self):
        count = self.get_argument("count", 20)
        files = FileService.instance().getRecent(count)
        self.render("file-list.html", files = files, key = "")

