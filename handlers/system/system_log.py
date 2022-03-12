# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/03/03 12:46:20
# @modified 2022/03/12 15:17:03
import os
import time
import xtemplate
import xauth
import xutils
import xconfig
import xmanager
from xutils import History
from xutils.imports import *
from xtemplate import BasePlugin

OPTION_HTML = '''
<div class="row card">

    <div class="x-tab-box row" data-style="btn" data-tab-key="type" data-tab-default="tail">
        <a class="x-tab" data-tab-value="tail">最近</a>
        <a class="x-tab" data-tab-value="head">最早</a>
        <a class="x-tab" data-tab-value="all">全部</a>
    </div>

    <p>
        <span>直接查看文件</span>
        <a href="/code/edit?path={{info_log_path}}">INFO日志</a>
        <span>|</span>
        <a href="/code/edit?path={{warn_log_path}}">WARN日志</a>
        <span>|</span>
        <a href="/code/edit?path={{error_log_path}}">ERROR日志</a>
        <span>|</span>
        <a href="/code/edit?path={{trace_log_path}}">TRACE日志</a>
    </p>
</div>

'''

def readlines(fpath):
    if not os.path.exists(fpath):
        return []
    with open(fpath, encoding="utf-8") as fp:
        return fp.readlines()

def get_log_path(date, level = "INFO"):
    month   = "-".join(date.split("-")[:2])
    dirname = os.path.join(xconfig.LOG_DIR, month)
    fname   = "xnote.%s.%s.log" % (date, level)
    return os.path.join(dirname, fname)
    
class LogHandler(BasePlugin):
    
    title    = 'xnote系统日志'
    # description = "查看系统日志"
    show_category = False
    category = 'system'
    editable = False
    rows = 0
    
    def handle(self, content):
        user_name = xauth.current_name()
        xmanager.add_visit_log(user_name, "/system/log")

        type = xutils.get_argument("type", "rev_tail")
        date = xutils.get_argument("date")

        if not date:
            date = time.strftime("%Y-%m-%d")

        fpath = get_log_path(date)
        self.render_options(date)

        if type == "rev_tail":
            lines = readlines(fpath)[-100:]
            lines.reverse()
            return "".join(lines)
        if type == "head":
            return ''.join(readlines(fpath)[:100])
        return xutils.readfile(fpath)
    
    def render_options(self, date):

        self.writehtml(OPTION_HTML, 
            info_log_path = get_log_path(date),
            warn_log_path = get_log_path(date, "WARN"),
            error_log_path = get_log_path(date, "ERROR"),
            trace_log_path = get_log_path(date, "TRACE"))
        

class HistoryHandler(object):
    """docstring for HistoryHandler"""

    @xauth.login_required("admin")
    def GET(self):
        xutils.get_argument("type", "")
        items = []
        if xconfig.search_history:
            items = xconfig.search_history.recent(50);
        return xtemplate.render("system/page/history.html", 
            show_aside = False,
            items = items)
        

xurls = (
    r"/system/history", HistoryHandler,
    r"/system/log", LogHandler
)
