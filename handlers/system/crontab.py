# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/03
# 

"""Description here"""
import web

import xauth
import xtemplate
import xmanager

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
        xmanager.instance().del_task(url)
        return self.default_request()
    
    @xauth.login_required("admin")
    def add_request(self):
        url = self.get_argument("url")
        interval = self.get_argument("interval", 10)
        xmanager.instance().add_task(url, interval)
        self.default_request()

