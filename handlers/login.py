# encoding=utf-8
import web
import hashlib
import xutils
import xauth
import xtemplate
import xtables

def get_real_ip():
    x_forwarded_for = web.ctx.env.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for != None:
        return x_forwarded_for.split(",")[0]
    return web.ctx.env.get("REMOTE_ADDR")

class handler:

    def POST(self):
        name = xutils.get_argument("username", "")
        pswd = xutils.get_argument("password", "")
        target = xutils.get_argument("target")
        users = xauth.get_users()
        error = ""

        db = xtables.get_record_table()
        value = "%s-%s" % (get_real_ip(), pswd)
        if name != "":
            db.insert(type="login", key=name, value=value, 
                ctime = xutils.format_datetime(), 
                cdate = xutils.format_date())

        if name in users:
            user = users[name]
            if pswd == user["password"]:
                web.setcookie("xuser", name, expires= 24*3600*30)
                pswd_md5 = xauth.get_password_md5(pswd)
                web.setcookie("xpass", pswd_md5, expires=24*3600*30)
                db = xtables.get_user_table()
                db.update(login_time=xutils.format_datetime(), where=dict(name=name))
                if target is None:
                    raise web.seeother("/")
                raise web.seeother(target)
            else:
                error = "user or password error"
        else:
            error = "user or password error"  
        return xtemplate.render("login.html", 
            username=name, 
            password=pswd,
            error = error)


    def GET(self):
        return xtemplate.render("login.html",
            username="",
            password="",
            error="")


