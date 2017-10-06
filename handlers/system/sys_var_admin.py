# encoding=utf-8

import web
import xauth
import xtemplate
import xmanager
import xconfig
import xutils
import xtables

def set_xconfig_bool(key):
    value = xutils.get_argument(key, "False")
    if value == "True":
        setattr(xconfig, key, True)
    else:
        setattr(xconfig, key, False)

class handler:
    """用户管理"""
    @xauth.login_required("admin")
    def GET(self):
        var_dict = {}
        var_dict["DATA_DIR"] = xconfig.DATA_DIR
        var_dict["IS_TEST"]  = xconfig.IS_TEST
        var_dict["OPEN_PROFILE"] = xconfig.OPEN_PROFILE
        return xtemplate.render("system/sys_var_admin.html", sys_var_dict = var_dict)

    @xauth.login_required("admin")
    def POST(self):
        data_dir = xutils.get_argument("DATA_DIR")
        xconfig.set_data_path(data_dir)

        set_xconfig_bool("IS_TEST")
        set_xconfig_bool("OPEN_PROFILE")

        # 先暴力解决
        xmanager.reload()
        raise web.seeother("/system/sys_var_admin")