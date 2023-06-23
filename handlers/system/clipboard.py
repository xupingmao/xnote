# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/07/18 22:55:08
# @modified 2019/07/20 22:42:44
import os
import xconfig
import xutils
import xmanager
from xtemplate import BasePlugin
from xutils import dateutil
from xutils import fsutil, dbutil

HTML = """
<!-- Html -->
<style>
.th-time {
    with: 30%;
}
.th-content {
    width: 70%;
}
</style>
<div class="card">
    {% if len(records) == 0 %}
        {% include common/text/empty_text.html %}
    {% end %}
    <table class="table">
        <tr>
            <th class="th-time">时间</th>
            <th class="th-content">内容</th>
        </tr>
    {% for r in records %}
        <tr>
            <td>{{r.create_time}}</td>
            <td>{{r.content}}</td>
        </tr>
    {% end %}
    </table>
</div>

<div class="card">
    {% include common/pagination.html %}
</div>
"""

dbutil.register_table("clip_log", "剪切板历史")

class ClipLogDO(xutils.Storage):

    def __init__(self):
        self.create_time = ""
        self.content = ""

class ClipLogDao:

    db = dbutil.get_table("clip_log")
    last_log_content = ""
    max_log_size = 500

    @classmethod
    def init(cls):
        last = cls.db.get_last()
        if last != None:
            cls.last_log_content = last.content

    @classmethod
    def add_log(cls, log_content=""):
        log_content = log_content.strip()
        if log_content == "":
            return
        if log_content == cls.last_log_content:
            return
        
        record = ClipLogDO()
        record.create_time = dateutil.format_datetime()
        record.content = log_content
        cls.db.insert(record)
        cls.last_log_content = log_content
        cls.clear_old_logs()
    
    @classmethod
    def clear_old_logs(cls):
        buf_size = 10
        if cls.db.count() > cls.max_log_size + buf_size:
            for record in cls.db.list(limit=buf_size):
                cls.db.delete(record)

    @classmethod
    def list_recent(cls, offset=0, limit=100):
        return cls.db.list(reverse=True, limit=limit)
    
    @classmethod
    def count(cls):
        return cls.db.count()


ClipLogDao.init()

class Main(BasePlugin):

    title = "剪切板记录"
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
        page = xutils.get_argument_int("page", 1)
        page_size = 20
        offset = (page-1) * page_size

        kw = xutils.Storage()
        kw.page = page
        kw.page_size = page_size
        kw.page_total = ClipLogDao.count()
        kw.records = ClipLogDao.list_recent(offset=offset, limit=page_size)
        self.writehtml(HTML, **kw)

    def on_init(self, context=None):
        # 插件初始化操作
        pass

@xmanager.listen("cron.minute")
def watch_clipboard(ctx=None):
    global last_paste
    if xutils.is_mac():
        # MAC下面通过定时来简单实现
        content = os.popen("pbpaste").read()
        ClipLogDao.add_log(content)
    else:
        try:
            import pyperclip
            content = pyperclip.paste()
            ClipLogDao.add_log(content)
        except:
            pass


xurls = (
    r"/system/clipboard-monitor", Main
)