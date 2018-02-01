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
        return xtemplate.render("system/user_list.html", 
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
        return self.GET()

xurls = (
    r"/system/user/list", ListHandler,
)