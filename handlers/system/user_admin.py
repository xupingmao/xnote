# encoding=utf-8

import web
import xauth
import xtemplate
import xmanager

class handler:
    """用户管理"""
    @xauth.login_required("admin")
    def GET(self):
        user_dict = xauth.get_users()
        test = xauth.get_user("test")
        print(" -- User -- ", test)
        return xtemplate.render("system/user_admin.html", 
            user_dict=user_dict)

    @xauth.login_required("admin")
    def POST(self):
        args = web.input()
        name = args.name
        password = args.password
        xauth.add_user(name, password)
        added = xauth.get_user(name)
        print(" -- User -- ", added)
        # 先暴力解决
        xmanager.reload()
        return self.GET()