# encoding=utf-8
# @modified 2022/04/06 12:39:18
import web
import xutils
import xauth
import xtemplate
from xutils import cacheutil, dbutil
from xutils import Storage
from xutils import webutil
import json

RETRY_LIMIT = 3
_user_log_db = dbutil.get_table("user_op_log")
_login_failed_count = cacheutil.PrefixedCache("login_failed_count:")

def get_real_ip():
    return webutil.get_real_ip()


def save_login_info(name, value, error=None):
    if name != "":
        real_ip = get_real_ip()
        now = xutils.format_datetime()
        detail = "登录IP: %s" % real_ip
        if error != None:
            detail += ",登录失败:%s" % error
        login_log = Storage(type="login", user_name=name,
                            ip=real_ip, ctime=now, detail=detail)
        _user_log_db.insert_by_user(name, login_log)


def save_login_error_count(name, count):
    _login_failed_count.put(name, count, 60)


class LoginHandler:

    def POST(self):
        name = xutils.get_argument_str("username", "")
        pswd = xutils.get_argument_str("password", "")
        error = self.do_login(name, pswd)
        return xtemplate.render("user/page/login.html",
                                show_aside=False,
                                username=name,
                                password=pswd,
                                error=error)

    def GET(self):
        return xtemplate.render("user/page/login.html",
                                show_aside=False,
                                show_nav=False,
                                username="",
                                password="",
                                error="")

    def do_login(self, name, pswd):
        target = xutils.get_argument_str("target")
        return self.do_login_with_redirect(name,pswd,target)


    def do_login_with_redirect(self,name, pswd, target=""):
        error = self.do_login_with_error(name, pswd)
        if error == "":
            if target == "":
                target = "/"
            raise web.found(target)
        return error
    
    def do_login_with_error(self, name, pswd, count=0):
        name = name.strip()
        pswd = pswd.strip()
        count = _login_failed_count.get(name, 0)
        assert isinstance(count, int)
        error = ""
        if name == "":
            error = "请输入登录名"
        elif pswd == "":
            error = "请输入密码"
        elif count >= RETRY_LIMIT:
            error = "重试次数过多"
        
        if error != "":
            return error
        
        user = xauth.get_user_by_name(name)

        if user == None:
            error = "用户名或密码错误"
            save_login_info(name, pswd, error)
            save_login_error_count(name, count + 1)
            return error
        else:
            if pswd == user["password"]:
                save_login_info(name, "success")

                try:
                    xauth.login_user_by_name(name, login_ip=get_real_ip())
                    return "" # 登录成功
                except Exception as e:
                    xutils.print_exc()
                    return str(e)
            else:
                error = "用户名或密码错误"
                save_login_info(name, pswd, error)
                save_login_error_count(name, count + 1)
        return error



class LoginAjaxHandler:
    def POST(self):
        print("enter the login ajax")
        print("the web data is :"+ str(web.data()))
        request_data = str(web.data(),'UTF-8')
        request_json = json.loads(request_data)
        name = request_json["username"]
        pswd = request_json["password"]

        hander = LoginHandler()
        error = hander.do_login_with_error(name,pswd)

        response = {}
        if ( error == ""):
            response['success'] = True
        else:
            response['success']  = False
            response['error']  = error
        return json.dumps(response)

xurls = (
    r"/login", LoginHandler,
    r"/login_ajax", LoginAjaxHandler
)
