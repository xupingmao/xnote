# encoding=utf-8
from handlers.base import *
import threading

__doc__ = """
展示系统使用的线程信息
"""

class handler(BaseHandler):

    def default_request(self):
        self.render("system/thread_info.html", thread_list = threading.enumerate())

name = "线程信息"
description = "线程信息"
