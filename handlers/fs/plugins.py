# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/03/22 22:57:39
# @modified 2018/05/08 23:01:25
import web
import os
import xconfig
import xutils
import xtemplate
import sys
import xauth
from xutils import ziputil

class ListHandler:
    @xauth.login_required("admin")
    def GET(self):
        path = xutils.get_argument("path")
        scripts = sorted(filter(lambda x: x.endswith(".py") and x.startswith("fs"), os.listdir(xconfig.SCRIPTS_DIR)))
        return xtemplate.render("fs/plugins.html", path = path, scripts = scripts)

class RunPluginHandler:

    @xauth.login_required("admin")
    def POST(self):
        sys.stdout.record()
        try:
            name = xutils.get_argument("name")
            path = xutils.get_argument("path")
            confirmed = xutils.get_argument("confirmed") == "true"
            vars = dict()
            xutils.load_script(name, vars = vars)
            main_func = vars.get("main", None)
            if main_func is not None:
                main_func(path = path, confirmed = confirmed)
            else:
                print("main(**kw)方法未定义")
        except Exception as e:
            xutils.print_exc()
        line = '-' * 30
        header = "执行 %s\n%s\n" % (name, line)
        footer = "\n%s\n执行完毕" % line
        result = header + sys.stdout.pop_record() + footer
        html = xutils.mark_text(result)
        html += '''<div><button onclick="runPlugin('%s', true)">确认执行</button></div>''' % name
        return dict(code="success", data = html)


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