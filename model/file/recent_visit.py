#coding:utf-8
from BaseHandler import *
from FileDB import *

class handler(BaseHandler):
    """show recent modified files"""
    def get(self):
        count = self.get_argument("count", 20)
        files = FileService.instance().getRecent(count)
        self.render("file-list.html", files = files, key = "")

