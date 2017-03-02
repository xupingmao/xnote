# encoding=utf-8

import web
import xauth
import xtemplate

class handler:
    """用户管理"""
    @xauth.login_required("admin")
    def GET(self):
        user_dict = xauth.get_users()
        return xtemplate.render("system/user_admin.html", 
            user_dict=user_dict)

    @xauth.login_required("admin")
    def POST(self):
        args = web.input()
        name = args.name
        password = args.password
        xauth.add_user(name, password)
        return self.GET()