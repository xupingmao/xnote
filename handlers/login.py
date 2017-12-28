# encoding=utf-8
import web
import hashlib

import xutils
import xauth
import xtemplate

class handler:

    def POST(self):
        name = xutils.get_argument("username", "")
        pswd = xutils.get_argument("password", "")
        target = xutils.get_argument("target")
        users = xauth.get_users()
        error = ""

        if name in users:
            user = users[name]
            if pswd == user["password"]:
                web.setcookie("xuser", name, expires= 24*3600*30)
                pswd_md5 = xauth.get_password_md5(pswd)
                web.setcookie("xpass", pswd_md5, expires=24*3600*30)
                if target is None:
                    raise web.seeother("/")
                raise web.seeother(target)
            else:
                error = "password error"
        else:
            error = "user not exists"
        return xtemplate.render("login.html", 
            username=name, 
            password=pswd,
            error = error)


    def GET(self):
        return self.POST()


