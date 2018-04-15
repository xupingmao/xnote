# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/03/22 22:57:39
# @modified 2018/04/15 20:26:48
import os
import xconfig
import xutils
import xtemplate
import xauth

class ListHandler:
    @xauth.login_required("admin")
    def GET(self):
        path = xutils.get_argument("path")
        scripts = sorted(filter(lambda x: x.endswith(".py") and x.startswith("fs"), os.listdir(xconfig.SCRIPTS_DIR)))
        return xtemplate.render("fs/plugins.html", path = path, scripts = scripts)

class RunPluginHandler:

	@xauth.login_required("admin")
	def POST(self):
		name = xutils.get_argument("name")
		path = xutils.get_argument("path")
		result = xutils.exec_script(name, vars = dict(path = path))
		return dict(code="success", data = result)

xurls = (
    r"/fs_api/plugins", ListHandler,
    r"/fs_api/run_plugin", RunPluginHandler,
)