# encoding=utf-8

import web

import xauth
import xtemplate
import xmanager


TASKLIST_CONF = "config/tasklist.ini"

class handler:
    def GET(self):
        task_dict = xmanager.instance().get_task_dict()
        
        return xtemplate.render("system/crontab.html", 
            task_dict = task_dict)
    
    @xauth.login_required("admin")
    def POST(self):
        args = web.input()
        url = args.url
        interval = int(args.interval)
        xmanager.instance().add_task(url, interval)
        return self.GET()

