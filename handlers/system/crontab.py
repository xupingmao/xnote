# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/03
# 

"""Description here"""
import os
import web
import xauth
import xtemplate
import xmanager
import xtables
import xutils
import xconfig

from handlers.base import BaseHandler

SCRIPT_EXT_TUPLE = (".py", ".bat", ".sh", ".command")

class handler:

    @xauth.login_required("admin")
    def GET(self):
        task_list = xmanager.get_task_list()
        for task in task_list:
            if task.url is None: task.url = ""
            task.url = xutils.unquote(task.url)
            parts = task.url.split("://")
            if len(parts) == 2:
                protol = parts[0]
                name   = parts[1]
                if protol == "script":
                    task.script_name = name
        scripts = []
        dirname = xconfig.SCRIPTS_DIR
        if os.path.exists(dirname):
            for fname in os.listdir(dirname):
                fpath = os.path.join(dirname, fname)
                if os.path.isfile(fpath) and fpath.endswith(SCRIPT_EXT_TUPLE):
                    scripts.append(fname)
        scripts.sort()

        def set_display_name(file):
            file.display_name = file.name if file.name != "" else file.url
            return file
        task_list = list(map(set_display_name, task_list))
        return xtemplate.render("system/crontab.html", task_list = task_list, scripts=scripts)


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
    r"/system/crontab",     handler, 
    r"/system/crontab/add", AddHandler,
    r"/system/crontab/remove", RemoveHandler
)

