# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/03
# Last modified on 2017/12/24

"""xnote定时任务配置"""
import os
import web
import xauth
import xtemplate
import xmanager
import xtables
import xutils
import xconfig

SCRIPT_EXT_TUPLE = (".py", ".bat", ".sh", ".command")


def get_cron_links():
    dirname = xconfig.SCRIPTS_DIR
    links = []
    API_PATH = os.path.join(xconfig.HANDLERS_DIR, "api")
    TOOLS_DIR = xconfig.TOOLS_DIR
    if os.path.exists(dirname):
        for fname in os.listdir(dirname):
            fpath = os.path.join(dirname, fname)
            if os.path.isfile(fpath) and fpath.endswith(SCRIPT_EXT_TUPLE):
                links.append("script://" + fname)
    links.sort()

    api_links = []
    for fname in os.listdir(API_PATH):
        fpath = os.path.join(API_PATH, fname)
        name, ext = os.path.splitext(fname)
        if name != "__init__" and os.path.isfile(fpath) and ext == ".py":
            api_links.append("/api/" + name)
    api_links.sort()
    links += api_links

    tool_links = []
    for fname in os.listdir(TOOLS_DIR):
        fpath = os.path.join(TOOLS_DIR, fname)
        name, ext = os.path.splitext(fname)
        if name != "__init__" and os.path.isfile(fpath) and ext == ".py":
            tool_links.append("/tools/" + name)
    tool_links.sort()
    links += tool_links
    return links

class CronEditHandler:

    @xauth.login_required("admin")
    def GET(self):
        id = xutils.get_argument("id", type=int)
        sched = xtables.get_schedule_table().select_one(where=dict(id=id))
        return xtemplate.render("system/crontab_edit.html", 
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

        db = xtables.get_schedule_table()
        if id == "" or id is None:
            db.insert(name=name, url=url, mtime=xutils.format_datetime(), 
                ctime=xutils.format_datetime(),
                tm_wday = tm_wday,
                tm_hour = tm_hour,
                tm_min = tm_min,
                message = message,
                sound = sound,
                webpage = webpage)
        else:
            id = int(id)
            db.update(where=dict(id=id), name=name, url=url, 
                mtime=xutils.format_datetime(),
                tm_wday = tm_wday,
                tm_hour = tm_hour,
                tm_min = tm_min,
                message = message,
                sound = sound,
                webpage = webpage)
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
        return xtemplate.render("system/crontab.html", 
            show_aside = False,
            task_list = task_list)


    @xauth.login_required("admin")
    def add_request_old(self):
        url      = xutils.get_argument("url")
        # interval = xutils.get_argument("interval", 10, type=int)
        repeat_type = xutils.get_argument("repeat_type", "day")
        pattern     = xutils.get_argument("pattern")

        if repeat_type == "interval":
            interval = int(pattern)
        else:
            interval = -1
            if pattern.count(":") == 1:
                # 如果是分钟默认加上秒
                pattern = pattern + ":00"

        db  = xtables.get_schedule_table()
        rows = db.select(where="url=$url", vars=dict(url=url))
        result = rows.first()
        if result is None:
            db.insert(url=url, 
                interval=interval, 
                pattern=pattern,
                ctime=xutils.format_time(), 
                mtime=xutils.format_time(),
                repeat_type=repeat_type)
        else:
            db.update(where=dict(url=url), 
                interval=interval, 
                pattern=pattern,
                mtime=xutils.format_time(), 
                repeat_type=repeat_type)

        xmanager.instance().load_tasks()
        raise web.seeother("/system/crontab")

class AddHandler:
    @xauth.login_required("admin")
    def POST(self):
        script_url = xutils.get_argument("script_url")
        url = xutils.get_argument("url")
        # url = xutils.quote_unicode(url)
        tm_wday = xutils.get_argument("tm_wday")
        tm_hour = xutils.get_argument("tm_hour")
        tm_min  = xutils.get_argument("tm_min")

        if script_url != "" and script_url != None:
            url = script_url

        if url == "":
            raise web.seeother("/system/crontab")

        db  = xtables.get_schedule_table()
        db.insert(url=url,
            ctime=xutils.format_time(),
            mtime=xutils.format_time(),
            tm_wday=tm_wday,
            tm_hour=tm_hour,
            tm_min=tm_min)
        xmanager.instance().load_tasks()
        raise web.seeother("/system/crontab")

class RemoveHandler:

    @xauth.login_required("admin")
    def POST(self):
        id = xutils.get_argument("id", type=int)
        xtables.get_schedule_table().delete(where=dict(id=id))
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

