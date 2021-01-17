# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/03/03 12:46:20
# @modified 2021/01/17 11:10:49
import os
import time
import xtemplate
import xauth
import xutils
import xconfig
from xutils import History
from xutils.imports import *
from xtemplate import BasePlugin

OPTION_HTML = '''
<div class="row card">
    <a class="x-tab-btn x-tab-default" href="?tab=rev_tail">最近</a>
    <a class="x-tab-btn" href="?tab=head">最早</a>
    <a class="x-tab-btn" href="?tab=all">全部</a>
</div>

'''

def readlines(fpath):
    if not os.path.exists(fpath):
        return []
    with open(fpath, encoding="utf-8") as fp:
        return fp.readlines()

def get_log_path(date):
    month   = "-".join(date.split("-")[:2])
    dirname = os.path.join(xconfig.LOG_DIR, month)
    fname   = "xnote.%s.INFO.log" % date
    return os.path.join(dirname, fname)
    
class LogHandler(BasePlugin):
    
    title    = 'xnote日志'
    description = "查看系统日志"
    show_category = False
    category = 'system'
    editable = False
    rows = 0
    
    def handle(self, content):
        self.render_options()
        type = xutils.get_argument("type", "rev_tail")
        date = xutils.get_argument("date")

        if not date:
            date = time.strftime("%Y-%m-%d")
        self.title = "xnote日志(%s)" % date

        fpath = get_log_path(date)
        if type == "rev_tail":
            lines = readlines(fpath)[-100:]
            lines.reverse()
            return "".join(lines)
        if type == "head":
            return ''.join(readlines(fpath)[:100])
        return xutils.readfile(fpath)
    
    def render_options(self):
        self.writehtml(OPTION_HTML)
        

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
