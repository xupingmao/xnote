# encoding=utf-8

import web
import xauth
import xtemplate
import xmanager
import xconfig
import xutils
import xtables

class handler:
    """用户管理"""
    @xauth.login_required("admin")
    def GET(self):
        var_dict = {}
        var_dict["DATA_DIR"] = xconfig.DATA_DIR
        var_dict["IS_TEST"]  = xconfig.IS_TEST
        return xtemplate.render("system/sys_var_admin.html", sys_var_dict = var_dict)

    @xauth.login_required("admin")
    def POST(self):
        data_dir = xutils.get_argument("DATA_DIR")
        xconfig.set_data_path(data_dir)

        is_test  = xutils.get_argument("IS_TEST", "False")
        if is_test == "True":
            xconfig.IS_TEST = True
        else:
            xconfig.IS_TEST = False


        # 先暴力解决
        xmanager.reload()
        xtables.init()
        raise web.seeother("/system/sys_var_admin")