# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/03
# @modified 2020/05/04 21:25:28

"""xnote定时任务配置"""
import os
import web
import json
from xutils import webutil
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xmanager
import xutils
from xnote.core import xconfig
from xnote.plugin.table_plugin import BaseTablePlugin
from xnote.plugin import DataTable, TableActionType, DataForm, FormRowType
from .dao_cron import CronJobDao

from xutils import dbutil

SCRIPT_EXT_TUPLE = (".py", ".bat", ".sh", ".command")


def get_api_links():
    API_PATH = os.path.join(xconfig.HANDLERS_DIR, "api")
    api_links = []
    for fname in os.listdir(API_PATH):
        fpath = os.path.join(API_PATH, fname)
        name, ext = os.path.splitext(fname)
        if name != "__init__" and os.path.isfile(fpath) and ext == ".py":
            api_links.append("/api/" + name)
    api_links.sort()
    return api_links

def get_tool_links():
    TOOLS_DIR = xconfig.TOOLS_DIR
    tool_links = []
    for fname in os.listdir(TOOLS_DIR):
        fpath = os.path.join(TOOLS_DIR, fname)
        name, ext = os.path.splitext(fname)
        if name != "__init__" and os.path.isfile(fpath) and ext == ".py":
            tool_links.append("/tools/" + name)
    tool_links.sort()
    return tool_links

def get_script_links():
    dirname = xconfig.SCRIPTS_DIR
    links = []
    if os.path.exists(dirname):
        for fname in os.listdir(dirname):
            fpath = os.path.join(dirname, fname)
            if os.path.isfile(fpath) and fpath.endswith(SCRIPT_EXT_TUPLE):
                links.append("script://" + fname)
    links.sort()
    return links

def get_cron_links():
    links = []
    links += get_api_links()
    # links += get_tool_links()
    links += get_script_links()
    return links

def display_time_rule(task):
    week = xutils.wday_map[task.tm_wday]
    hour = "每小时"
    if task.tm_hour != "*":
        hour = "%s时" % task.tm_hour

    if task.tm_min == "*":
        minute = "每分钟"
    elif task.tm_min == "mod5":
        minute = "每5分钟"
    else:
        minute = "%s分" % task.tm_min

    return "%s %s %s" % (week, hour, minute)

def add_cron_task(url, mtime, ctime, tm_wday, tm_hour, tm_min, 
        name = "", message="", sound=0, webpage=0):
    id  = dbutil.timeseq()
    key = "schedule:%s" % id
    data = dict(id = id, name=name, url=url, mtime=xutils.format_datetime(), 
        ctime   = xutils.format_datetime(),
        tm_wday = tm_wday,
        tm_hour = tm_hour,
        tm_min  = tm_min,
        message = message,
        sound   = sound,
        webpage = webpage)
    dbutil.put(key, data)
    return id

class CronEditHandler:

    @xauth.login_required("admin")
    def GET(self):
        id  = xutils.get_argument("id")
        key = "schedule:%s" % id
        sched = dbutil.get(key)
        return xtemplate.render("system/page/crontab_edit.html", 
            item = sched, 
            links = get_cron_links())

class ListHandler(BaseTablePlugin):

    title = "定时任务"
    require_admin = True
    show_aside = True
    PAGE_HTML = BaseTablePlugin.TABLE_HTML

    def handle_page(self):
        table = DataTable()
        table.add_head("编号", "index")
        table.add_head("任务", "display_name", link_field="script_url")
        table.add_head("时间", "time_rule")

        table.add_action("编辑", type=TableActionType.edit_form, link_field="edit_url")
        table.add_action("删除", type=TableActionType.confirm, link_field="delete_url", 
                         msg_field="delete_msg", css_class="btn danger")

        task_list = xmanager.get_task_list()
        index = 0
        for task in task_list:
            index += 1
            if task.url is None: 
                task.url = ""
            
            task.url = xutils.unquote(task.url)
            parts = task.url.split("://")
            task.protocol = "unknown"
            if len(parts) == 2:
                protocol = parts[0]
                name   = parts[1]
                task.protocol = protocol
                if protocol == "script":
                    task.script_name = name
            
            if task.name != "":
                task.display_name = task.name
            else:
                task.display_name = task.url

            if task.protocol == "script":
                task.display_name = task.url
            
            if task.protocol == "script":
                task.script_url = f"{xconfig.WebConfig.server_home}/code/edit?path={task.script_name}&type=script"
            else:
                task.script_url = None

            task.index = index
            task.time_rule = display_time_rule(task)

            if task.id:
                task.edit_url = f"?action=edit&id={task.id}"
                task.delete_url = f"?action=delete&id={task.id}"
                task.delete_msg = f"确认删除任务【{task.display_name}】吗?"

            table.add_row(task)

        kw = xutils.Storage()
        kw.table = table
        return self.response_page(**kw)
    
    def handle_edit(self):
        id  = xutils.get_argument("id")
        key = f"schedule:{id}"
        sched = dbutil.db_get_object(key)
        assert sched != None

        form = DataForm()
        form.add_row("id", "id", value=str(sched.id), css_class="hide")
        form.add_row("标题", "name", value=str(sched.name))

        row = form.add_row("触发链接", "url", type=FormRowType.select, value=str(sched.url))
        for link in get_cron_links():
            row.add_option(link, link)

        row = form.add_row("周", "tm_wday", type=FormRowType.select, value=str(sched.tm_wday))
        for wday in xutils.wday_map:
            row.add_option(xutils.wday_map[wday], wday)

        row = form.add_row("小时", "tm_hour", type=FormRowType.select, value=str(sched.tm_hour))
        row.add_option("每小时", "*")
        for hour in range(24):
            row.add_option(str(hour), str(hour))

        row = form.add_row("分钟", "tm_min", type=FormRowType.select, value=str(sched.tm_min))
        row.add_option("每分钟", "*")
        row.add_option("每5分钟", "mod5")
        for tm_min in range(0, 60, 5):
            row.add_option(str(tm_min), str(tm_min))

        form.add_row("信息", "message", type=FormRowType.textarea, value=str(sched.message))
        
        kw = xutils.Storage()
        kw.form = form
        return self.response_form(**kw)
    
    def handle_save(self):
        data = xutils.get_argument_str("data")
        data_dict = json.loads(data)

        id   = data_dict.get("id")
        name = data_dict.get("name")
        url  = data_dict.get("url")
        tm_wday = data_dict.get("tm_wday")
        tm_hour = data_dict.get("tm_hour")
        tm_min  = data_dict.get("tm_min")
        message = data_dict.get("message")
        sound = int(data_dict.get("sound", "0"))
        webpage = int(data_dict.get("webpage", "0"))

        # db = xtables.get_schedule_table()
        if id == "" or id is None:
            return webutil.FailedResult(code="403", message="不允许新增任务")
        else:
            key = "schedule:%s" % id
            data = dbutil.db_get_object(key)
            if data is not None:
                data.mtime = xutils.format_datetime()
                data.name  = name
                data.url   = url
                data.tm_wday = tm_wday
                data.tm_hour = tm_hour
                data.tm_min  = tm_min
                data.message = message
                data.sound   = sound
                data.webpage = webpage
                dbutil.put(key, data)
            else:
                return webutil.FailedResult(code="404", message="记录不存在")
            
        xmanager.load_tasks()
        return webutil.SuccessResult()

    def handle_delete(self):
        id = xutils.get_argument_str("id")
        job_info = CronJobDao.get_by_id(id)
        if job_info == None:
            return webutil.FailedResult(code="404", message="记录不存在")
        CronJobDao.delete_by_id(id)
        xmanager.load_tasks()
        return webutil.SuccessResult()


class AddHandler:
    @xauth.login_required("admin")
    def POST(self):
        script_url = xutils.get_argument("script_url")
        url = xutils.get_argument("url")
        # url = xutils.quote_unicode(url)
        tm_wday = xutils.get_argument("tm_wday")
        tm_hour = xutils.get_argument("tm_hour")
        tm_min  = xutils.get_argument("tm_min")
        format  = xutils.get_argument("_format")

        if script_url != "" and script_url != None:
            url = script_url

        if url == "":
            raise web.seeother("/system/crontab")

        sched_id = add_cron_task(url=url,
            ctime=xutils.format_time(),
            mtime=xutils.format_time(),
            tm_wday=tm_wday,
            tm_hour=tm_hour,
            tm_min=tm_min)
        xmanager.instance().load_tasks()

        if format == "json":
            return dict(code = "success", data = dict(id = sched_id))
        raise web.seeother("/system/crontab")

class RemoveHandler:

    @xauth.login_required("admin")
    def POST(self):
        id = xutils.get_argument("id")
        key = "schedule:%s" % id
        dbutil.delete(key)
        xmanager.load_tasks()
        raise web.seeother("/system/crontab")

    def GET(self):
        return self.POST()

xurls=(
    r"/system/crontab",     ListHandler, 
    r"/system/crontab/remove", RemoveHandler,
)

