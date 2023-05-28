# encoding=utf-8
"""
展示系统使用的线程信息
"""
import xauth
import threading
import xtemplate
import xutils
import xmanager
from xutils import MyStdout

def get_thread_log(thread):
    records = MyStdout.get_records(thread)
    if records is None:
        return "[无]"
    return xutils.mark_text("".join(records))

def get_handler_name(thread):
    handler_class = xmanager.handler_local.get_handler_class_by_thread(thread)
    if handler_class != None:
        return handler_class
    return None

class ThreadInfoHandler:

    @xauth.login_required("admin")
    def GET(self):
        kw = xutils.Storage()
        kw.thread_list = threading.enumerate()
        kw.get_handler_name = get_handler_name
        return xtemplate.render("system/page/thread_info.html", **kw)

xurls = (
    r"/system/thread_info", ThreadInfoHandler,
)