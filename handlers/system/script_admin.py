# encoding=utf-8
# Created by xupingmao on 2017/05/24
# 系统脚本管理
from __future__ import print_function
import os
import gc
import web
import six
import xauth
import xutils
import xconfig
import xtemplate

from xutils import u
sys = xutils.sys

SCRIPT_EXT_LIST = (
    ".bat", 
    ".vbs", 
    ".sh", 
    ".command",
    ".py"
)

def get_default_shell_ext():
    if xutils.is_mac():
        return ".command"
    elif xutils.is_windows():
        return ".bat"
    return ".sh"

class SaveHandler:

    @xauth.login_required("admin")
    def POST(self):
        name = xutils.get_argument("name")
        content = xutils.get_argument("content")
        dirname = xconfig.SCRIPTS_DIR
        path = os.path.join(dirname, name)
        content = content.replace("\r", "")
        xutils.savetofile(path, content)
        raise web.seeother("/system/script_admin/edit?name="+xutils.quote(name))

class DeleteHandler:

    @xauth.login_required("admin")
    def POST(self):
        name = xutils.get_argument("name")
        dirname = xconfig.SCRIPTS_DIR
        path = os.path.join(dirname, name)
        os.remove(path)
        raise web.seeother("/system/script_admin")

class ExecuteHandler:

    @xauth.login_required("admin")
    def GET(self):
        return self.POST()

    @xauth.login_required("admin")
    def POST(self):
        name = xutils.get_argument("name")
        ret = xutils.exec_script(name)
        return dict(code="success", message="", data=ret)

class handler:

    @xauth.login_required("admin")
    def GET(self):
        op = xutils.get_argument("op")
        name = xutils.get_argument("name", "")
        error = xutils.get_argument("error", "")
        dirname = xconfig.SCRIPTS_DIR

        content = ""
        if op == "edit":
            content = xutils.readfile(os.path.join(dirname, name))
        if op == "add" and name != "":
            basename, ext = os.path.splitext(name)
            if ext not in SCRIPT_EXT_LIST:
                name = basename + get_default_shell_ext()
                path = os.path.join(dirname, name)
            if os.path.exists(path):
                raise web.seeother(xutils.quote_unicode("/system/script_admin?error=%r已存在" % name))
            with open(path, "wb") as fp:
                pass

        shell_list = []
        
        if os.path.exists(dirname):
            for fname in os.listdir(dirname):
                fpath = os.path.join(dirname, fname)
                if os.path.isfile(fpath) and fpath.endswith(SCRIPT_EXT_LIST):
                    shell_list.append(fname)
        shell_list.sort()
        return xtemplate.render("system/script_admin.html", 
            op = op,
            name = name,
            content = content,
            shell_list = shell_list,
            error = error)

    @xauth.login_required("admin")
    def POST(self):
        op = xutils.get_argument("op")
        name = xutils.get_argument("name", "")
        dirname = xconfig.SCRIPTS_DIR
        path = os.path.join(dirname, name)
        # print(op, name)
        basename, ext = os.path.splitext(name)
        if op == "add" and name != "":
            if ext not in SCRIPT_EXT_LIST:
                name = basename + get_default_shell_ext()
                path = os.path.join(dirname, name)
            if os.path.exists(path):
                raise web.seeother(xutils.quote_unicode("/system/script_admin?error=%r已存在" % name))
            with open(path, "wb") as fp:
                pass
        elif op == "save":
            content = xutils.get_argument("content")
            content.replace("\r", "")
            xutils.savetofile(path, content)
        raise web.seeother("/system/script_admin")

class EditHandler:

    @xauth.login_required("admin")
    def GET(self):
        op = xutils.get_argument("op")
        name = xutils.get_argument("name", "")
        error = xutils.get_argument("error", "")
        dirname = xconfig.SCRIPTS_DIR

        path = os.path.join(dirname, name)
        if not os.path.exists(path):
            content = ""
        else:
            content = xutils.readfile(path)

        return xtemplate.render("system/script_admin.html", 
            op = "edit",
            name = name,
            content = content,
            shell_list = [],
            error = error)

xurls = (
    r"/system/script_admin", handler,
    r"/system/script_admin/edit", EditHandler,
    r"/system/script/edit", EditHandler,
    r"/system/script_admin/save", SaveHandler,
    r"/system/script_admin/execute", ExecuteHandler,
    r"/system/script_admin/delete", DeleteHandler
)


