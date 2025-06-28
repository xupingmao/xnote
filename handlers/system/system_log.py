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
from xnote.plugin import TableActionType, LinkConfig

uv_db = dbutil.get_table("uv")

OPTION_HTML = '''
<div class="row">
    <script src="{{_server_home}}/_static/js/base/jq-ext.js"></script>
    
    {% include system/component/system_log_tab.html %}

    <div class="card">
        {% if log_type == "file" %}
            <div class="x-tab-box btn-style dark row" data-tab-key="type" data-tab-default="tail">
                <a class="x-tab" data-tab-value="tail">最新</a>
                <a class="x-tab" data-tab-value="head">最早</a>
                <a class="x-tab" data-tab-value="all">全部</a>
            </div>

            <div class="row">
                <span>直接查看文件</span>
                <a href="{{_server_home}}/code/edit?path={{info_log_path}}">INFO日志</a>
                <span>|</span>
                <a href="{{_server_home}}/code/edit?path={{warn_log_path}}">WARN日志</a>
                <span>|</span>
                <a href="{{_server_home}}/code/edit?path={{error_log_path}}">ERROR日志</a>
                <span>|</span>
                <a href="{{_server_home}}/code/edit?path={{trace_log_path}}">TRACE日志</a>
            </div>
        {% end %}

        {% if log_type == "mem" %}
            {% init log_name = "" %}
            {% init log_not_found = False %}

            <span>日志名称</span>
            <select value="{{log_name}}" class="logger-name-select">
                {% for logger in mem_loggers %}
                    <option value="{{logger.name}}">{{logger.name}}</option>
                {% end %}

                {% if log_not_found and log_name != "" %}
                    <option value="{{log_name}}">{{log_name}}</option>
                {% end %}
            </select>
        {% end %}
    </div>
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

ASIDE_HTML = """
{% include system/component/admin_nav.html %}
"""


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


class LogHandler(BasePlugin):

    title = '系统日志'
    # description = "查看系统日志"
    show_aside = True
    editable = False
    rows = 0
    parent_link = LinkConfig.app_index
    category = "admin"

    def get_arg_date(self):
        date = xutils.get_argument("date")

        if not date:
            date = time.strftime("%Y-%m-%d")

        return date

    def handle_mem_log(self):
        log_name = xutils.get_argument("log_name", "")
        loggers = logutil.MemLogger.list_loggers()
        for logger in loggers:
            if logger.name == log_name:
                return logger.text()

        if len(loggers) > 0 and log_name == "":
            return loggers[0].text()

        return "<empty>"

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
        
        self.show_aside = True
        self.write_aside(ASIDE_HTML)

        if log_type == "mem":
            return self.handle_mem_log()

        if log_type == "file":
            return self.handle_file_log()

        return ""

    def render_options(self, date):
        log_type = xutils.get_argument("log_type", "file")
        log_name = xutils.get_argument("log_name", "")
        loggers = logutil.MemLogger.list_loggers()
        log_not_found = not iter_exists(lambda x: x.name == log_name, loggers)

        self.writehtml(OPTION_HTML,
                       log_type=log_type,
                       mem_loggers=loggers,
                       info_log_path=get_log_path(date),
                       log_name=log_name,
                       log_not_found=log_not_found,
                       warn_log_path=get_log_path(date, "WARN"),
                       error_log_path=get_log_path(date, "ERROR"),
                       trace_log_path=get_log_path(date, "TRACE"))


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
    
    NAV_HTML = """
    {% include system/component/system_log_tab.html %}
    
    <div class="card x-tab-box" data-tab-key="table_name" data-tab-default="sys_log">
        {% for table_name in table_name_list %}
            <a class="x-tab" data-tab-value="{{table_name}}" href="{{_server_home}}/system/log/db?log_type=db&table_name={{table_name}}">{{table_name}}</a>
        {% end %}
    </div>
    """
        
    page_html = NAV_HTML + BaseTablePlugin.TABLE_HTML
    
    table_type_dict = {
        "sys_log": "kv",
        "user_op_log": "sql",
    }
    
    def get_page_html(self):
        return self.page_html
    
    def handle_page(self):
        table_name_list = ["sys_log", "user_op_log"]
        table_name = xutils.get_argument_str("table_name", "sys_log")
        page = xutils.get_argument_int("page", 1)
        page_size = 20
        
        table_type = self.table_type_dict.get(table_name, "sql")
        
        table = DataTable()
        table.add_head("时间", "ctime", width="200px")
        table.add_head("用户", "user_name", width="100px")
        table.add_head("内容", "content", width = "min:200px")
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
        kw.table_name_list = table_name_list
        kw.page = page
        kw.page_total = page_total
        kw.page_url = f"?log_type=db&table_name={table_name}&page="
        
        return self.response_page(**kw)

xurls = (
    r"/system/log", LogHandler,
    r"/system/log/db", DatabaseLogHandler,
    r"/system/log/visit", LogVisitHandler,
)
