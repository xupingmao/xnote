#coding:utf-8
from BaseHandler import *
from FileDB import *

class handler(BaseHandler):
    """show recent modified files"""
    def default_request(self):
        s_days = self.get_argument("days", 7)
        days = int(s_days)
        files = FileService.instance().get_recent_modified(days)
        self.render("file-list.html", files = files, key = "")

    def json_request(self):
        s_days = self.get_argument("days", 7)
        days = int(s_days)
        files = FileService.instance().get_recent_modified(days)
        return files

