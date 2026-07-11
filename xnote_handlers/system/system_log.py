# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2018/03/03 12:46:20
@LastEditors  : xupingmao
@LastEditTime : 2024-09-16 17:21:35
@Description  : 描述
"""

import os
import time
import xutils

from collections import deque
from xnote.core import xauth
from xnote.core import xconfig
from xnote.core import xmanager
from xnote.core import xtables
from xutils import logutil, dbutil, webutil, dateutil, jsonutil
from xutils import textutil
from xutils import Storage
from xnote.core.xtemplate import BasePlugin
from xutils.functions import iter_exists
from xnote.plugin.table_plugin import BaseTablePlugin
from xnote.plugin import DataTable
from xnote.plugin import TableActionType
from xnote_handlers.config import LinkConfig, TabConfig
from xnote.service import SystemLogService, SystemLogLevel, SystemLogType
from xnote_handlers.config import AsideConfig
from xnote.webui import TabBox, Card, RowPanel, Textarea
from xnote.plugin import BasePluginV2

uv_db = dbutil.get_table("uv")

OPTION_HTML = '''
<div class="row">
    <script src="{{_server_home}}/_static/js/base/jq-ext.js"></script>
    
    <script>
    $(function () {
        $(".output-textarea").scrollBottom();
        $(".logger-name-select").change(function (e) {
            var oldHref = window.location.href;
            var newHref = addUrlParam(oldHref, "log_name", $(e.target).val());
            window.location.href = newHref;
        });
    })
    </script>
</div>
'''

def get_system_log_tab():
    card = Card()
    card.add(TabConfig.system_log_tab)
    return card

def readlines(fpath):
    if not os.path.exists(fpath):
        return []
    with open(fpath, encoding="utf-8") as fp:
        return fp.readlines()


def get_log_path(date, level="INFO"):
    month = "-".join(date.split("-")[:2])
    dirname = os.path.join(xconfig.LOG_DIR, month)
    fname = "xnote.%s.%s.log" % (date, level)
    return os.path.join(dirname, fname)


def read_tail_lines(fpath, lines):
    if not os.path.exists(fpath):
        return []

    q = deque()

    with open(fpath, encoding="utf-8") as fp:
        while True:
            line = fp.readline(1024)
            if line is None or len(line) == 0:
                break
            q.append(line)
            if len(q) > lines:
                q.popleft()

    return "".join(q)


class LogHandler(BasePluginV2):
    title = '系统日志'
    require_admin = True
    # description = "查看系统日志"
    show_aside = True
    editable = False
    rows = 0
    parent_link = LinkConfig.app_index
    category = "admin"

    def get_arg_date(self):
        date = xutils.get_argument_str("date")

        if not date:
            date = time.strftime("%Y-%m-%d")

        return date

    def handle_file_log(self):
        type = xutils.get_argument("type", "tail")
        date = self.get_arg_date()

        fpath = get_log_path(date)

        if type == "tail":
            return read_tail_lines(fpath, 100)

        if type == "head":
            return ''.join(readlines(fpath)[:100])

        return xutils.readfile(fpath, limit=1024 * 1024)

    def handle(self, content):
        user_name = xauth.current_name_str()
        xmanager.add_visit_log(user_name, "/system/log")

        log_type = xutils.get_argument("log_type", "file")
        date = self.get_arg_date()

        self.render_options(date)
        self.update_aside(AsideConfig.admin_aside_html)
        
        if log_type == "file":
            return self.handle_file_log()

        return ""

    def render_options(self, date):
        log_type = xutils.get_argument("log_type", "file")
        log_name = xutils.get_argument("log_name", "")
        
        kw = Storage()
        kw.log_type=log_type
        kw.log_name=log_name

        first_tab = get_system_log_tab()
        
        self.add_component(first_tab)
        
        if log_type == "file":
            self.render_file(date)
            
        if log_type == "mem":
            self.render_mem()
    
    def render_file(self, date: str):
        card = Card()
        tab = TabBox(tab_key="type", tab_default="tail", css_class="btn-style")
        tab.add_item("最新", value="tail")
        tab.add_item("最早", value="head")
        tab.add_item("全部", value="all")
        
        info_log_path=get_log_path(date)
        warn_log_path=get_log_path(date, "WARN")
        error_log_path=get_log_path(date, "ERROR")
        trace_log_path=get_log_path(date, "TRACE")
        
        row = RowPanel()
        row.add_span("直接查看文件")
        row.add_link(text="INFO日志", href=f"/code/edit?path={info_log_path}")
        row.add_item_sep()
        row.add_link(text="WARN日志", href=f"/code/edit?path={warn_log_path}")
        row.add_item_sep()
        row.add_link(text="ERROR日志", href=f"/code/edit?path={error_log_path}")
        row.add_item_sep()
        row.add_link(text="TRACE日志", href=f"/code/edit?path={trace_log_path}")
        
        card.add(tab)
        card.add(row)
        
        self.add_component(card)
        
    
    def render_mem(self):
        loggers = logutil.MemLogger.list_loggers()
        card = Card()
        tab_default = ""
        if len(loggers) > 0:
            tab_default = loggers[0].name
        tab = TabBox(tab_key="log_name", tab_default=tab_default, css_class="btn-style")
        for logger in loggers:
            tab.add_item(title=logger.name, value=logger.name)
        
        card.add(tab)

        
        log_content = ""
        log_name = xutils.get_argument("log_name", tab_default)
        loggers = logutil.MemLogger.list_loggers()
        for logger in loggers:
            if logger.name == log_name:
                log_content = logger.text()

        if len(loggers) > 0 and log_name == "":
            log_content = loggers[0].text()

        textarea = Textarea(log_content, css_class="row", rows="20")
        card.add(textarea)
        
        self.add_component(card)        

class UvRecord(Storage):

    def __init__(self) -> None:
        self.id = 0
        self.ip = ""
        self.site = ""
        self.date = ""
        self.count = 0
    
class LogVisitHandler:

    def do_get(self, site="", ip=""):
        uv_db = xtables.get_table_by_name("site_visit_log")        
        date = dateutil.format_date()
        db_record = uv_db.select_first(where = dict(date = date, ip = ip, site = site))

        if db_record == None:
            record = UvRecord()
            record.count += 1
            record.date = date
            record.site = site
            record.ip = ip
            record.pop("id")
            uv_db.insert(**record)
        else:
            assert isinstance(db_record, dict)
            record = UvRecord()
            record.update(db_record)
            record.count+=1
            record.ip = ip
            uv_db.update(where=dict(id=record.id), **record)
        return "console.log('log visit success');"
    
    def GET(self):
        site = xutils.get_argument_str("site", "xnote")
        ip = webutil.get_real_ip()
        if ip == None:
            return
        return self.do_get(site=site, ip=ip)

class DatabaseLogHandler(BaseTablePlugin):
    title = "数据库日志"
    parent_link = LinkConfig.app_index
    
    table_name_list = ["system_log", "user_op_log"]
    table_type_dict = {
        "sys_log": "kv",
        "user_op_log": "sql",
        "system_log": "sql",
    }
    default_table_name = "system_log"
    
    def get_db_tab(self):
        tab = TabBox(tab_key="table_name", tab_default=self.default_table_name, css_class="btn-style")
        for name in self.table_name_list:
            tab.add_item(title=name, value=name, href=f"/system/log/db?log_type=db&table_name={name}")
        
        card = Card()
        card.add(tab)
        return card
    
    def handle_page(self):
        table_name = xutils.get_argument_str("table_name", self.default_table_name)
        page = xutils.get_argument_int("page", 1)
        page_size = 20
        
        self.update_aside(AsideConfig.admin_aside_html)
        self.add_component(get_system_log_tab())
        self.add_component(self.get_db_tab())

        if table_name == "system_log":
            return self.handle_system_log_page(table_name)
        
        table_type = self.table_type_dict.get(table_name, "sql")
        
        table = DataTable()
        table.add_head("时间", "ctime", width="200px")
        table.add_head("用户", "user_name", width="100px")
        table.add_head("内容", "content", min_width="200px")
        page_total = 0
        
        if table_type == "kv":
            page_total = 10000
            db = dbutil.get_table(table_name=table_name)
            offset = (page-1)*page_size
            for item in db.iter(offset=offset, limit=20, reverse=True):
                row = {}
                row["ctime"] = item.pop("ctime", "-")
                row["content"] = textutil.get_short_text(jsonutil.tojson(item), 1024)
                table.add_row(row)
        
        if table_type == "sql":
            page_total = 10000
            db = xtables.get_table_by_name(table_name=table_name)
            offset = (page-1)*page_size
            pk_name = db.table_info.pk_name
            for item in db.select(offset=offset, limit=page_size, order=f"`{pk_name}` DESC"):
                row = {}
                user_id = item.pop("user_id", 0)
                user_name = xauth.UserDao.get_name_by_id(user_id=user_id)
                row["ctime"] = item.pop("ctime", "")
                row["content"] = textutil.get_short_text(jsonutil.tojson(item), 1024)
                row["user_name"] = user_name
                table.add_row(row)

        kw = Storage()
        kw.table = table
        kw.table_name_list = self.table_name_list
        kw.page = page
        kw.page_total = page_total
        kw.page_url = f"?table_name={table_name}&page="
        kw.tab_default = "db"
        
        return self.response_page(**kw)
    
    def handle_system_log_page(self, table_name: str):
        page = xutils.get_argument_int("page", 1)
        page_size = 20

        table = DataTable()
        table.add_head("时间", "create_time_str", width="200px")
        table.add_head("类型", "log_type", width="50px")
        table.add_head("级别", "log_level", width="50px")
        table.add_head("内容", "log_content_short", min_width="200px", detail_field="log_content")
        page_total = SystemLogService.count_logs()

        offset = (page-1)*page_size
        for row in SystemLogService.get_logs(offset=offset, limit=page_size):
            row["log_content_short"] = textutil.get_short_text(row.log_content, 100)
            row["create_time_str"] = dateutil.format_datetime(row.create_time, is_ms=True)
            table.add_row(row)

        kw = Storage()
        kw.table = table
        kw.table_name_list = self.table_name_list
        kw.page = page
        kw.page_total = page_total
        kw.page_url = f"?table_name={table_name}&page="
        kw.tab_default = "db"
        
        return self.response_page(**kw)

xurls = (
    r"/system/log", LogHandler,
    r"/system/log/db", DatabaseLogHandler,
    r"/system/log/visit", LogVisitHandler,
)
