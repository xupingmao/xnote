# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/03/22 22:57:39
# @modified 2018/04/19 23:20:48
import web
import os
import xconfig
import xutils
import xtemplate
import xauth
from util import ziputil

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


class DownloadPluginsHandler:

    @xauth.login_required("admin")
    def GET(self):
        bufsize = 1024 * 100
        dirname = xconfig.SCRIPTS_DIR
        outpath = os.path.join(dirname, "fs-plugins.zip")
        ziputil.zip_dir(dirname, outpath = outpath, filter = lambda x: os.path.basename(x).startswith("fs") and x.endswith(".py"))
        web.header("Content-Disposition", "attachment; filename=fs-plugins.zip")
        with open(outpath, "rb") as fp:
            buf = fp.read(bufsize)
            while buf:
                yield buf
                buf = fp.read(bufsize)

xurls = (
    r"/fs_api/plugins", ListHandler,
    r"/fs_api/run_plugin", RunPluginHandler,
    r"/fs_api/plugins/download", DownloadPluginsHandler
)