# encoding=utf-8
# @modified 2022/04/06 12:39:18
import web
import xutils
from xnote.core import xauth
from xnote.core import xtemplate
from xutils import cacheutil, dbutil
from xutils import Storage
from xutils import webutil
import json

from . import dao as user_dao

RETRY_LIMIT = 3
_login_failed_count = cacheutil.PrefixedCache("login_failed_count:")

def get_real_ip():
    return webutil.get_real_ip()


def save_login_info(name, error=None):
    if name != "":
        real_ip = get_real_ip()
        detail = "登录IP: %s" % real_ip
        if error != None:
            detail += ",登录失败:%s" % error
        user_id = xauth.UserDao.get_id_by_name(name)
        if user_id == 0:
            user_id = -1
            detail += f",login_name:{name}"
        
        log = user_dao.UserOpLog()
        log.detail = detail
        log.type = user_dao.UserOpTypeEnum.login.value
        log.user_id = user_id
        log.ip = real_ip
        user_dao.UserOpLogDao.create_op_log(log)


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
            save_login_info(name, error)
            save_login_error_count(name, count + 1)
            return error
        else:
            if xauth.encode_password(pswd, user.salt) == user.password_md5:
                save_login_info(name)

                try:
                    xauth.login_user_by_name(name, login_ip=get_real_ip())
                    return "" # 登录成功
                except Exception as e:
                    xutils.print_exc()
                    return str(e)
            else:
                error = "用户名或密码错误"
                save_login_info(name, error)
                save_login_error_count(name, count + 1)
        return error



class LoginAjaxHandler:
    def POST(self):
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

class NewAccountLoginHandler:
    def POST(self):
        request_data = str(web.data(),'UTF-8')
        print("enter login "+request_data)
        request_json = json.loads(request_data)
        name = request_json["username"]
        pswd = request_json["password"]

        hander = LoginHandler()
        error = hander.do_login_with_error(name,pswd)

        response = {}
        response["type"] = "account"
        if ( error == ""):
            response['status'] = "ok"
        else:
            response['status']  = "error"
            response['errorMsg']  = error
        return json.dumps(response)

xurls = (
    r"/login", LoginHandler,
    r"/login_ajax", LoginAjaxHandler,
    r"/login/account_login", NewAccountLoginHandler
)
