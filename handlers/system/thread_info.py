# encoding=utf-8
"""
展示系统使用的线程信息
"""
import threading
import xutils

from xnote.core import xauth, xtemplate, xmanager
from xutils import Storage
from xutils import MyStdout
from xutils import textutil
from xnote.plugin.table_plugin import BaseTablePlugin

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

class ThreadInfoHandler(BaseTablePlugin):

    require_admin = True
    title = "线程列表"
    PAGE_HTML = BaseTablePlugin.TABLE_HTML
    show_aside = True
    show_right = True

    def get_aside_html(self):
        return xtemplate.render_text("{% include system/component/admin_nav.html %}")

    def handle_page(self):
        table = self.create_table()
        table.default_head_style.width = "25%"
        table.add_head("编号", "no")
        table.add_head("Name", "name")
        table.add_head("处理器", "handler")
        table.add_head("详情", "detail_short", detail_field="detail")
        
        for idx, info in enumerate(threading.enumerate()):
            row = {}
            row["no"] = idx + 1
            row["name"] = info.name
            row["handler"] = get_handler_name(thread=info)
            detail = textutil.tojson(info.__dict__, format=True)
            row["detail"] = detail
            row["detail_short"] = textutil.get_short_text(detail, 100)
            table.add_row(row)

        kw = Storage()
        kw.table = table
        kw.page = 1
        kw.page_max = 1
        kw.page_url = "?page="

        return self.response_page(**kw)

xurls = (
    r"/system/thread_info", ThreadInfoHandler,
)