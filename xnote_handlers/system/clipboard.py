# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/07/18 22:55:08
# @modified 2019/07/20 22:42:44
import xutils
import logging

from xnote.core import xmanager
from xnote.core.xtemplate import BasePlugin
from xnote.core import xtables
from xnote.plugin import sidebar
from xnote.plugin.table_plugin import BaseTablePlugin
from xutils import dateutil
from xutils import dbutil, BaseDataRecord
from xutils import textutil
from xutils import webutil
from xnote.webui import Card
from xnote_handlers.config import get_system_log_tab

ASIDE_HTML = """
{% include system/component/admin_nav.html %}
"""

class ClipLogRecord(BaseDataRecord):
    def __init__(self):
        self.id = 0
        self.ctime = dateutil.format_datetime()
        self.mtime = dateutil.format_datetime()
        self.content = ""

    def to_save_dict(self):
        result = dict(**self)
        result.pop("id")
        return result

class ClipLogDao:

    db = xtables.get_table_by_name("clip_log_v2")
    max_log_count = 500
    max_content_size = 1024 * 1024 # 1MB

    @classmethod
    def init(cls):
        pass

    @classmethod
    def find_by_content(cls, content=""):
        record = cls.db.select_first(where = dict(content = content))
        return ClipLogRecord.from_dict_or_None(record)
    
    @classmethod
    def find_last(cls):
        record = cls.db.select_first(order = "mtime desc")
        return ClipLogRecord.from_dict_or_None(record)

    @classmethod
    def add_log(cls, log_content=""):
        log_content = log_content.strip()
        if log_content == "":
            return
        
        if len(log_content) > cls.max_content_size:
            logging.warning("clipboard data too large")
            log_content = log_content[:cls.max_content_size]
        
        current_time = dateutil.format_datetime()
        last = cls.find_last()
        if last != None and last.content == log_content:
            return

        old = cls.find_by_content(content=log_content)
        if old is not None:
            cls.db.update(where = dict(id = old.id), mtime = current_time)
            return
        
        record = ClipLogRecord()
        record.ctime = current_time
        record.mtime = current_time
        record.content = log_content
        cls.db.insert(**record.to_save_dict())
        cls.last_log_content = log_content
        cls.clear_old_logs()
    
    @classmethod
    def clear_old_logs(cls):
        buf_size = 10
        if cls.db.count() > cls.max_log_count + buf_size:
            for record in cls.db.select(limit=buf_size, order="mtime"):
                cls.db.delete(where = dict(id = record.id))

    @classmethod
    def list_recent(cls, offset=0, limit=100):
        result = cls.db.select(offset=offset, limit=limit, order="mtime desc")
        return ClipLogRecord.from_dict_list(result)
    
    @classmethod
    def get_by_id(cls, id=0):
        record = cls.db.select(where = dict(id = id))
        return ClipLogRecord.from_dict_or_None(record)
    
    @classmethod
    def count(cls):
        return cls.db.count()


ClipLogDao.init()

class Main(BaseTablePlugin):

    title = "剪贴板日志"
    # 提示内容
    description = ""
    # 访问权限
    require_admin = True
    # 插件分类 {note, dir, system, network}
    category = "system"

    editable = False
    show_aside = True
    

    def get_aside_html(self):
        return sidebar.get_admin_sidebar_html()

    def handle_page(self):
        # 输入框的行数
        watch_clipboard()
        op = xutils.get_argument_str("op")
        page = xutils.get_argument_int("page", 1)
        page_size = 20
        offset = (page-1) * page_size
        
        card = Card()
        card.add(get_system_log_tab("clip"))
        self.add_component(card)

        if op == "detail":
            return self.handle_detail()
        
        records = ClipLogDao.list_recent(offset=offset, limit=page_size)
        
        table = self.create_table()
        table.default_head_style.min_width = "100px"
        table.add_head("时间", "mtime", min_width="200px")
        table.add_head("内容", "content_short", detail_field="content")

        for item in records:
            item.content_short = textutil.get_short_text(item.content, 200)
            table.add_row(item)


        kw = xutils.Storage()
        kw.table = table
        kw.page = page
        kw.page_size = page_size
        kw.page_total = ClipLogDao.count()
        kw.tab_default = "clip"
        
        return self.response_page(**kw)

    def handle_detail(self):
        id = xutils.get_argument_int("id")
        return webutil.SuccessResult(
            data = ClipLogDao.get_by_id(id)
        )

    def on_init(self, context=None):
        # 插件初始化操作
        pass

MAX_CLIP_SIZE = 1024*1024 # 1MB

@xmanager.listen("cron.minute")
def watch_clipboard(ctx=None):
    try:
        import pyperclip
        content = pyperclip.paste()
        if len(content) > MAX_CLIP_SIZE:
            logging.warning("clip content too large: %s, max_size: %s", len(content), MAX_CLIP_SIZE)
            return
        ClipLogDao.add_log(content)
    except:
        xutils.print_exc()


xurls = (
    r"/system/clipboard-monitor", Main
)