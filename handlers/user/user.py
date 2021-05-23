# encoding=utf-8
# @modified 2021/05/23 12:26:10
import web
import xauth
import xtemplate
import xmanager
import xutils
from xutils import textutil

class ListHandler:
    """用户管理"""

    @xauth.login_required("admin")
    def GET(self):
        user_dict = xauth.get_users()
        return xtemplate.render("user/page/user_list.html", 
            show_aside = False,
            user_info = None,
            user_dict=user_dict)

    @xauth.login_required("admin")
    def POST(self):
        name     = xutils.get_argument("name")
        password = xutils.get_argument("password")
        error = xauth.add_user(name, password)
        added = xauth.get_user(name)
        # 先暴力解决
        xmanager.reload()
        raise web.seeother("/system/user?name=%s" % name)

class UserHandler:

    @xauth.login_required("admin")
    def GET(self):
        name = xutils.get_argument("name", "")
        user_info = None
        if name != "":
            user_info = xauth.get_user(name)
        return xtemplate.render("user/page/user_manage.html", 
            show_aside = False,
            name = name,
            user_info = user_info, 
            user_dict = xauth.get_users())

    @xauth.login_required("admin")
    def POST(self):
        name     = xutils.get_argument("name")
        password = xutils.get_argument("password")
        user_info = xauth.get_user(name)
        if user_info is None:
            raise Exception("用户不存在:%s" % name)

        user_info.password = password
        xauth.update_user(name, user_info)

        raise web.seeother("/system/user?name=%s" % name)

class AddHandler:

    @xauth.login_required("admin")
    def POST(self):
        name   = xutils.get_argument("name")
        result = xauth.create_user(name, textutil.random_string(6))
        if result["code"] == "success":
            # 重新加载系统
            xmanager.reload()
        return result

class RemoveHandler:

    @xauth.login_required("admin")
    def POST(self):
        name = xutils.get_argument("name")
        xauth.delete_user(name)
        return dict(code="success")

class UserInfoHandler:

    @xauth.login_required()
    def GET(self):
        user = xauth.current_user()
        return xtemplate.render("user/page/userinfo.html", user = user)

class SessionInfoAjaxHandler:

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
        return xauth.list_user_session_detail(user_name)

xurls = (
    r"/user/add",  AddHandler,
    r"/user/list",  ListHandler,
    r"/user/info",   UserInfoHandler,
    r"/user/session", SessionInfoAjaxHandler,
    
    r"/system/user", UserHandler,
    r"/system/user/list", ListHandler,
    r"/system/user/remove", RemoveHandler,
)