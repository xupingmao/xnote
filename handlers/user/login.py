# encoding=utf-8
# @modified 2020/01/25 12:25:38
import web
import time
import hashlib
import xutils
import xauth
import xtemplate
from xutils import dateutil, cacheutil, dbutil

RETRY_LIMIT = 3

def get_real_ip():
    x_forwarded_for = web.ctx.env.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for != None:
        return x_forwarded_for.split(",")[0]
    return web.ctx.env.get("REMOTE_ADDR")

def save_login_info(name, value):
    message = "%s-%s" % (get_real_ip(), value)
    if name != "":
        dbutil.insert("record:login", dict(type="login", 
            key = name, value = message, 
            ctime = xutils.format_datetime(), 
            cdate = xutils.format_date()))

def save_login_error_count(name, count):
    cacheutil.set("login.fail.count#%s" % name, count, 60)

class handler:

    def POST(self):
        name = xutils.get_argument("username", "")
        pswd = xutils.get_argument("password", "")
        target = xutils.get_argument("target")
        users = xauth.get_users()
        error = ""
        count = cacheutil.get("login.fail.count#%s" % name, 0)
        name  = name.strip()
        pswd  = pswd.strip()
        if count >= RETRY_LIMIT:
            error = "重试次数过多"
        elif name in users:
            user = users[name]
            if pswd == user["password"]:
                save_login_info(name, "success")
                xauth.write_cookie(name)
                xauth.update_user(name, dict(login_time=xutils.format_datetime()))                
                if target is None:
                    raise web.seeother("/")
                raise web.seeother(target)
            else:
                error = "用户名或密码错误"
                save_login_info(name, pswd)
                save_login_error_count(name, count + 1)
        else:
            error = "用户名或密码错误"
            save_login_info(name, pswd)
            save_login_error_count(name, count + 1)

        return xtemplate.render("user/login.html", 
            show_aside = False,
            username   = name, 
            password   = pswd,
            error      = error)


    def GET(self):
        return xtemplate.render("user/login.html",
            show_aside=False,
            username="",
            password="",
            error="")


xurls = (
    r"/login", handler
)
