# encoding=utf-8
"""
展示系统使用的线程信息
"""
import xauth
import threading
import xtemplate
import xutils
from xutils import MyStdout

def get_thread_log(thread):
    records = MyStdout.get_records(thread)
    if records is None:
        return "[无]"
    return xutils.mark_text("".join(records))

class ThreadInfoHandler:

    @xauth.login_required("admin")
    def GET(self):
        return xtemplate.render("system/thread_info.html", 
            show_aside = False,
            thread_list = threading.enumerate())

class ThreadLogsHandler:

    @xauth.login_required("admin")
    def GET(self):
        result_dict = MyStdout._instance.result_dict
        return xtemplate.render("system/thread_logs.html", 
            result_dict = result_dict, 
            get_thread_log = get_thread_log)

xurls = (
    r"/system/thread_info", ThreadInfoHandler,
    r"/system/thread_logs", ThreadLogsHandler
)