# encoding=utf-8
"""
展示系统使用的线程信息
"""
import threading
import xtemplate
import xutils

class handler:

    def GET(self):
        return xtemplate.render("system/thread_info.html", 
            show_aside = False,
            thread_list = threading.enumerate())

name = "线程信息"
description = "线程信息"
