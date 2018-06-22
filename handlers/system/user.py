# encoding=utf-8
import web
import xauth
import xtemplate
import xmanager
import xutils

class ListHandler:
    """用户管理"""

    @xauth.login_required("admin")
    def GET(self):
        user_dict = xauth.get_users()
        return xtemplate.render("system/user_manage.html", 
            user_info = None,
            user_dict=user_dict)

    @xauth.login_required("admin")
    def POST(self):
        name     = xutils.get_argument("name")
        password = xutils.get_argument("password")
        xauth.add_user(name, password)
        added = xauth.get_user(name)
        xutils.log("Add user {}", added)
        # 先暴力解决
        xmanager.reload()
        raise web.seeother("/system/user?name="+name)

class UserHandler:

    @xauth.login_required("admin")
    def GET(self):
        name = xutils.get_argument("name", "")
        user_info = None
        if name != "":
            user_info = xauth.get_user(name)
        return xtemplate.render("system/user_manage.html", 
            name = name,
            user_info = user_info, 
            user_dict = xauth.get_users())

class RemoveHandler:

    @xauth.login_required("admin")
    def POST(self):
        name = xutils.get_argument("name")
        xauth.remove_user(name)
        return dict(code="success")

xurls = (
    r"/system/user", UserHandler,
    r"/system/user/list", ListHandler,
    r"/system/user/remove", RemoveHandler
)