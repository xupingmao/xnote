# encoding=utf-8
# @modified 2020/07/05 18:48:15
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
        return xtemplate.render("user/user_list.html", 
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
        return xtemplate.render("user/user_manage.html", 
            show_aside = False,
            name = name,
            user_info = user_info, 
            user_dict = xauth.get_users())

class AddHandler:

    @xauth.login_required("admin")
    def POST(self):
        name   = xutils.get_argument("name")
        result = xauth.add_user(name, textutil.random_string(6))
        if result["code"] == "success":
            # 重新加载系统
            xmanager.reload()
        return result

class RemoveHandler:

    @xauth.login_required("admin")
    def POST(self):
        name = xutils.get_argument("name")
        xauth.remove_user(name)
        return dict(code="success")

xurls = (
    r"/user/add",  AddHandler,
    r"/user/list",  ListHandler,
    
    r"/system/user", UserHandler,
    r"/system/user/list", ListHandler,
    r"/system/user/remove", RemoveHandler
)