# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/07/18 22:55:08
# @modified 2019/07/20 22:42:44
import os
import re
import math
import time
import web
import xconfig
import xutils
import xauth
import xmanager
import xtables
import xtemplate
from xtemplate import BasePlugin
from xutils import cacheutil, dateutil, Storage
from xutils import fsutil

HTML = """
<!-- Html -->
<div class="card">
    {% for r in records %}
        <p>{{attrget(r, "time")}} {{attrget(r, "content")}}</p>
    {% end %}
</div>
"""

last_paste = None

def get_current_log_path():
    return os.path.join(xconfig.LOG_DIR, "clipboard", "clip-" + dateutil.format_date() + ".log")

class Main(BasePlugin):

    title = "剪切板"
    # 提示内容
    description = ""
    # 访问权限
    required_role = "admin"
    # 插件分类 {note, dir, system, network}
    category = 'note'

    editable = False
    
    def handle(self, input):
        # 输入框的行数
        watch_clipboard()
        self.rows = 0
        self.btn_text = '添加'
        fpath = get_current_log_path()
        return fsutil.readfile(fpath, raise_error = False)

    def on_init(self, context=None):
        # 插件初始化操作
        pass

@xmanager.listen("cron.minute")
def watch_clipboard(ctx=None):
    global last_paste
    if xutils.is_mac():
        # MAC下面通过定时来简单实现
        info = os.popen("pbpaste").read()
        if info:
            info = info.strip()
            if info != last_paste:
                dirname = os.path.join(xconfig.LOG_DIR, "clipboard")
                fsutil.makedirs(dirname)

                fpath = get_current_log_path()
                fsutil.writeline(fpath, "\n----- %s -----" % dateutil.format_time(), "ab")
                fsutil.writeline(fpath, info, "ab")
                last_paste = info
xurls = (
    r"/system/clipboard-monitor", Main
)