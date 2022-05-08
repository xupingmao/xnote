# encoding=utf-8
# @modified 2022/04/06 12:39:18
import web
import xutils
import xauth
import xtemplate
from xutils import cacheutil, dbutil
from xutils import Storage
from xutils import webutil

RETRY_LIMIT = 3

dbutil.register_table("user_op_log", "用户操作日志表", check_user = True)

_user_log_db = dbutil.get_table("user_op_log")

def get_real_ip():
    return webutil.get_real_ip()

def save_login_info(name, value, error = None):
    if name != "":
        real_ip = get_real_ip()
        now = xutils.format_datetime()
        detail = "登录IP: %s" % real_ip
        if error != None:
            detail += ",登录失败:%s" % error
        login_log = Storage(type = "login", user_name = name, ip = real_ip, ctime = now, detail = detail)
        _user_log_db.insert_by_user(name, login_log)

def save_login_error_count(name, count):
    cacheutil.set("login.fail.count#%s" % name, count, 60)

class LoginHandler:

    def POST(self):
        name = xutils.get_argument("username", "")
        pswd = xutils.get_argument("password", "")
        error = ""
        count = cacheutil.get("login.fail.count#%s" % name, 0)
        name  = name.strip()
        pswd  = pswd.strip()

        if name == "":
            error = "请输入登录名"
        elif pswd == "":
            error = "请输入密码"
        elif count >= RETRY_LIMIT:
            error = "重试次数过多"
        else:
            error = self.do_login(name, pswd, count)

        return xtemplate.render("user/page/login.html", 
            show_aside = False,
            username   = name, 
            password   = pswd,
            error      = error)


    def GET(self):
        return xtemplate.render("user/page/login.html",
            show_aside=False,
            username="",
            password="",
            error="")

    def do_login(self, name, pswd, count = 0):
        target = xutils.get_argument("target", "")
        user = xauth.get_user_by_name(name)
        error = ""

        if user == None:
            error = "用户名或密码错误"
            save_login_info(name, pswd, error)
            save_login_error_count(name, count + 1)
        else:
            if pswd == user["password"]:
                save_login_info(name, "success")
                
                xauth.login_user_by_name(name, login_ip = get_real_ip())

                if target == "":
                    raise web.found("/")
                raise web.found(target)
            else:
                error = "用户名或密码错误"
                save_login_info(name, pswd, error)
                save_login_error_count(name, count + 1)
        return error

xurls = (
    r"/login", LoginHandler
)
