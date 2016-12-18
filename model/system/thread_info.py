from BaseHandler import *
import threading

class handler(BaseHandler):

    def default_request(self):
        self.render("system/thread_info.html", thread_list = threading.enumerate())

name = "线程信息"
description = "线程信息"
