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


TASKLIST_CONF = "config/tasklist.ini"

class handler(BaseHandler):

    @xauth.login_required("admin")
    def default_request(self):
        self.task_dict = xmanager.instance().get_task_dict()
        self.render(task_dict = self.task_dict)

    @xauth.login_required("admin")
    def del_request(self):
        url = self.get_argument("url")
        xtables.get_schedule_table().delete(where=dict(url=url))
        xmanager.instance().load_tasks()
        return self.default_request()
    
    @xauth.login_required("admin")
    def add_request(self):
        url      = xutils.get_argument("url")
        interval = xutils.get_argument("interval", 10, type=int)

        db  = xtables.get_schedule_table()
        rows = db.select(where="url=$url", vars=dict(url=url))
        result = rows.first()
        if result is None:
            db.insert(url=url, interval=interval, 
                ctime=xutils.format_time(), mtime=xutils.format_time())
        else:
            db.update(where=dict(url=url), interval=interval, mtime=xutils.format_time())

        xmanager.instance().load_tasks()
        self.default_request()

