# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/03
# 

"""Description here"""
import web

import xauth
import xtemplate
import xmanager
import xtables
import xutils

from handlers.base import BaseHandler


class handler(BaseHandler):

    @xauth.login_required("admin")
    def default_request(self):
        self.task_list = xmanager.instance().get_task_list()
        self.render("system/crontab.html", task_list = self.task_list)

    @xauth.login_required("admin")
    def del_request(self):
        # url = self.get_argument("url")
        id = xutils.get_argument("id", type=int)
        xtables.get_schedule_table().delete(where=dict(id=id))
        xmanager.instance().load_tasks()
        raise web.seeother("/system/crontab")

    @xauth.login_required("admin")
    def add_request(self):
        url = xutils.get_argument("url")
        tm_wday = xutils.get_argument("tm_wday")
        tm_hour = xutils.get_argument("tm_hour")
        tm_min  = xutils.get_argument("tm_min")

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

