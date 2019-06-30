# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/03/03 12:46:20
# @modified 2019/07/01 00:30:45
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
    <a class="btn" href="?type=tail_rev">tail(倒序)</a>
    <a class="btn" href="?type=tail">tail</a>
    <a class="btn" href="?type=head">head</a>
    <a class="btn" href="?type=all">all</a>
</div>

'''

def readlines(fpath):
    if not os.path.exists(fpath):
        return []
    with open(fpath, encoding="utf-8") as fp:
        return fp.readlines()

def get_log_path(date):
    fname = "xnote.%s.log" % date
    return os.path.join(xconfig.LOG_DIR, fname)
    
class LogHandler(BasePlugin):
    
    title = 'xnote日志'
    category = 'system'
    editable = False
    
    def handle(self, content):
        self.rows = 0
        self.render_options()
        type = xutils.get_argument("type", "tail_rev")
        date = xutils.get_argument("date")
        if not date:
            date = time.strftime("%Y-%m-%d")
        self.title = "xnote日志(%s)" % date

        fpath = get_log_path(date)
        if type == "tail":
            return ''.join(readlines(fpath)[-100:])
        if type == "tail_rev":
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
        return xtemplate.render("system/history.html", 
            show_aside = False,
            items = items)
        

xurls = (
    r"/system/history", HistoryHandler,
    r"/system/log", LogHandler
)
