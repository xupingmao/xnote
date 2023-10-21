# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/03
# @modified 2020/05/04 21:25:28

"""xnote定时任务配置"""
import os
import web
import xauth
import xtemplate
import xmanager
import xtables
import xutils
import xconfig
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
        
class CronSaveHandler:
    
    @xauth.login_required("admin")
    def POST(self):
        id   = xutils.get_argument("id")
        name = xutils.get_argument("name")
        url  = xutils.get_argument("url")
        tm_wday = xutils.get_argument("tm_wday")
        tm_hour = xutils.get_argument("tm_hour")
        tm_min  = xutils.get_argument("tm_min")
        message = xutils.get_argument("message")
        sound_value = xutils.get_argument("sound")
        webpage_value = xutils.get_argument("webpage")
        sound = 1 if sound_value == "on" else 0
        webpage = 1 if webpage_value == "on" else 0

        # db = xtables.get_schedule_table()
        if id == "" or id is None:
            id = add_cron_task(name=name, url=url, mtime=xutils.format_datetime(), 
                ctime   = xutils.format_datetime(),
                tm_wday = tm_wday,
                tm_hour = tm_hour,
                tm_min  = tm_min,
                message = message,
                sound   = sound,
                webpage = webpage)
        else:
            key = "schedule:%s" % id
            data = dbutil.get(key)
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
        xmanager.load_tasks()
        raise web.seeother("/system/crontab")

class ListHandler:

    @xauth.login_required("admin")
    def GET(self):
        task_list = xmanager.get_task_list()
        for task in task_list:
            if task.url is None: task.url = ""
            task.url = xutils.unquote(task.url)
            parts = task.url.split("://")
            task.protocol = "unknown"
            if len(parts) == 2:
                protocol = parts[0]
                name   = parts[1]
                task.protocol = protocol
                if protocol == "script":
                    task.script_name = name

        def set_display_name(file):
            file.display_name = file.name if file.name != "" else file.url
            if file.protocol == "script":
                file.display_name = file.url
            return file
        task_list = list(map(set_display_name, task_list))
        return xtemplate.render("system/page/crontab.html", 
            show_aside = False,
            task_list = task_list,
            display_time_rule = display_time_rule)

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
    r"/system/crontab/add", AddHandler,
    r"/system/crontab/remove", RemoveHandler,
    r"/system/crontab/edit", CronEditHandler,
    r"/system/crontab/save", CronSaveHandler
)

