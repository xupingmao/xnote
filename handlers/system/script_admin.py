# encoding=utf-8
# Created by xupingmao on 2017/05/24
# 系统脚本管理

import os
import web

import xauth
import xutils
import xconfig
import xtemplate


SCRIPT_EXT_LIST = (
    ".bat", 
    ".vbs", 
    ".sh", 
    ".command"
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
        raise web.seeother("/system/script_admin?op=edit&name="+xutils.quote(name))

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
        dirname = xconfig.SCRIPTS_DIR
        path = os.path.join(dirname, name)
        path = os.path.abspath(path)
        ret  = 0
        if name.endswith(".command"):
            # Mac os Script
            os.system("chmod +x " + path)
            ret = os.system("open " + path)
        elif path.endswith(".bat"):
            os.system("start %s" % path)
        elif path.endswith(".sh"):
            os.system("chmod +x " + path)
        elif path.endswith(".vbs"):
            os.system("start %s" % path)
            # TODO linux怎么处理?
        return dict(code="success", message="", ret=ret)

class handler:

    @xauth.login_required("admin")
    def GET(self):
        op = xutils.get_argument("op")
        name = xutils.get_argument("name", "")
        dirname = xconfig.SCRIPTS_DIR

        content = ""
        if op == "edit":
            content = xutils.readfile(os.path.join(dirname, name))

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
            shell_list = shell_list)

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
            with open(path, "wb") as fp:
                pass
        elif op == "save":
            content = xutils.get_argument("content")
            content.replace("\r", "")
            xutils.savetofile(path, content)
        raise web.seeother("/system/script_admin")

xurls = (
    r"/system/script_admin", handler,
    r"/system/script_admin/save", SaveHandler,
    r"/system/script_admin/execute", ExecuteHandler,
    r"/system/script_admin/delete", DeleteHandler
)


