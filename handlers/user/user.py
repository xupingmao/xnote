# encoding=utf-8
# @modified 2022/04/04 14:01:57
import web
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xmanager
import xutils
import math
from xutils import textutil
from xutils import Storage
from xutils import dbutil
from xutils import webutil
from . import dao

OP_LOG_TABLE = xauth.UserOpLogDao


def create_op_log(user_name, op_type, detail):
    ip = webutil.get_real_ip()
    log = dao.UserOpLog()
    log.user_id = xauth.UserDao.get_id_by_name(user_name)
    log.ip = ip
    log.type = op_type
    log.detail = detail
    dao.UserOpLogDao.create_op_log(log)


class ListHandler:
    """用户管理"""

    @xauth.login_required("admin")
    def GET(self):
        page = xutils.get_argument_int("page", 1)
        page_size = xutils.get_argument_int("page_size", 10)
        offset = (page-1) * page_size
        assert offset >= 0

        total = xauth.UserModel.count()

        kw = Storage()
        kw.user_info = None
        kw.show_aside = False
        kw.user_list = xauth.UserModel.list(offset = offset, limit = page_size)
        kw.page = page
        kw.page_size = page_size
        kw.page_max = math.ceil(total/page_size)//1

        return xtemplate.render("user/page/user_list.html", **kw)

    @xauth.login_required("admin")
    def POST(self):
        name = xutils.get_argument("name")
        password = xutils.get_argument("password")
        error = xauth.create_user(name, password)
        added = xauth.get_user(name)
        # 先暴力解决
        xmanager.reload()
        raise web.seeother("/system/user?name=%s" % name)


class UserHandler:

    @xauth.login_required("admin")
    def GET(self):
        name = xutils.get_argument_str("name")
        user_info = None
        if name != "":
            user_info = xauth.get_user(name)
        
        user_id = xauth.UserDao.get_id_by_name(name)
        kw = Storage()
        kw.name = name
        kw.user_info = user_info
        kw.log_list = OP_LOG_TABLE.list_by_user(user_id=user_id, limit=100)

        return xtemplate.render("user/page/user_manage.html", **kw)

    @xauth.login_required("admin")
    def POST(self):
        name = xutils.get_argument("name")
        password = xutils.get_argument_str("password")
        user_info = xauth.get_user(name)
        if user_info is None:
            raise Exception("用户不存在:%s" % name)

        user_info.password = password
        xauth.update_user(name, user_info)

        raise web.seeother("/system/user?name=%s" % name)


class AddHandler:

    @xauth.login_required("admin")
    def POST(self):
        name = xutils.get_argument("name")
        return xauth.create_user(name, textutil.random_string(6))


class RemoveHandler:

    @xauth.login_required("admin")
    def POST(self):
        user_id = xutils.get_argument_int("user_id")
        xauth.UserModel.delete_by_id(user_id)
        return dict(code="success")


class UserInfoHandler:

    @xauth.login_required()
    def GET(self):
        user = xauth.current_user()
        return xtemplate.render("user/page/userinfo.html", user=user)

class UserInfoAjaxHandler:
    def getDesensitizedUserInfo(self):
        user = xauth.current_user()
        assert user != None
        mobile = ''
        if (user.mobile != None and user.mobile != ''):
            mobile = user.mobile[:3] + '****' + user.mobile[7:]
        return dict(name=user.name, phone=mobile)


    @xauth.login_required()
    def POST(self):
       return self.getDesensitizedUserInfo()

    @xauth.login_required()
    def GET(self):
        return self.getDesensitizedUserInfo()


class SessionInfoAjaxHandler:

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
        return xauth.list_user_session_detail(user_name)


class ChangePasswordHandler:

    def GET(self, error=""):
        """获取页面, 修改密码后也需要跳转到这里，所以不能校验登录态"""
        old_password = xutils.get_argument("old_password", "")
        new_password = xutils.get_argument("new_password", "")
        return xtemplate.render("user/page/change_password.html",
                                old_password=old_password, new_password=new_password, error=error)

    @xauth.login_required()
    def POST(self):
        user_name = xauth.current_name()
        old_password = xutils.get_argument("old_password", "")
        new_password = xutils.get_argument("new_password", "")
        error = ""

        if old_password == "":
            return self.GET(error="旧的密码为空")
        if new_password == "":
            return self.GET(error="新的密码为空")

        try:
            xauth.check_old_password(user_name, old_password)
            xauth.update_user(user_name, Storage(password=new_password))
            create_op_log(user_name, "change_password", "修改密码")
        except Exception as e:
            return self.GET(error=str(e))

        return self.GET(error=error)

class ResetPasswordHandler:

    @xauth.login_required("admin")
    def POST(self):
        user_name = xutils.get_argument_str("user_name")
        new_password = xutils.random_number_str(8)
        xauth.update_user(user_name, Storage(password=new_password))
        create_op_log(user_name, dao.UserOpTypeEnum.reset_password.value, "重置密码")
        return dict(code="success", data=new_password)

class UserOpLogHandler:

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name_str()
        user_id = xauth.UserDao.get_id_by_name(user_name)
        log_list = OP_LOG_TABLE.list_by_user(user_id, limit=100)
        return xtemplate.render("user/page/user_op_log.html", log_list=log_list)


xurls = (
    r"/user/add",  AddHandler,
    r"/user/list",  ListHandler,
    r"/user/info",   UserInfoHandler,
    r"/user/info_ajax", UserInfoAjaxHandler,
    r"/user/session", SessionInfoAjaxHandler,
    r"/user/change_password", ChangePasswordHandler,
    r"/user/op_log", UserOpLogHandler,

    r"/system/user", UserHandler,
    r"/system/user/list", ListHandler,
    r"/system/user/remove", RemoveHandler,
    r"/system/user/reset_password", ResetPasswordHandler,
)
