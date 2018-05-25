# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/03/22 22:57:39
# @modified 2018/05/25 20:16:42
import web
import os
import xconfig
import xutils
import xtemplate
import sys
import xauth
from xutils import ziputil


def get_display_name(name):
    return name[3:]

class ListHandler:
    @xauth.login_required("admin")
    def GET(self):
        show_menu = (xutils.get_argument("show_menu") == "true")
        path = xutils.get_argument("path")
        if path == "" or path == None:
            path = xconfig.DATA_DIR
        scripts = sorted(filter(lambda x: x.endswith(".py") and x.startswith("fs-"), os.listdir(xconfig.SCRIPTS_DIR)))
        return xtemplate.render("fs/plugins.html", 
            path = path, 
            scripts = scripts, 
            get_display_name = get_display_name,
            show_menu = show_menu)

class RunPluginHandler:

    @xauth.login_required("admin")
    def POST(self):
        sys.stdout.record()
        try:
            name = xutils.get_argument("name")
            path = xutils.get_argument("path")
            confirmed = xutils.get_argument("confirmed") == "true"
            input = xutils.get_argument("input", "")
            vars = dict()
            xutils.load_script(name, vars = vars)
            main_func = vars.get("main", None)
            if main_func is not None:
                main_func(path = path, confirmed = confirmed, input = input)
            else:
                print("main(**kw)方法未定义")
        except Exception as e:
            xutils.print_exc()
        
        header = "执行 %s<hr>" % name
        # footer = "\n%s\n执行完毕，请确认下一步操作" % line
        footer = ''
        result = sys.stdout.pop_record()
        html = header + xutils.mark_text(result)
        html += '''<input id="inputText" class="col-md-12" placeholder="请输入参数" value="%s">''' % input
        html += '''<div><button class="btn-danger" onclick="runPlugin('%s', true)">确认执行</button></div>''' % name
        return dict(code="success", data = html)


class DownloadPluginsHandler:

    @xauth.login_required("admin")
    def GET(self):
        bufsize = 1024 * 100
        dirname = xconfig.SCRIPTS_DIR
        outpath = os.path.join(dirname, "fs-plugins.zip")
        ziputil.zip_dir(dirname, outpath = outpath, filter = lambda x: os.path.basename(x).startswith("fs-") and x.endswith(".py"))
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