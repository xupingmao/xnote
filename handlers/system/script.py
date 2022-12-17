# encoding=utf-8
# Created by xupingmao on 2017/05/24
# 系统脚本管理
from __future__ import print_function
import os
import sys
import gc
import web
import xauth
import xutils
import xconfig
import xtemplate
from xutils import u
from xutils import six

SCRIPT_EXT_LIST = (
    ".bat", 
    ".vbs", 
    ".sh", 
    ".command",
    ".py"
)

template_file = "system/page/script.html"

def get_default_shell_ext():
    if xutils.is_mac():
        return ".command"
    elif xutils.is_windows():
        return ".bat"
    return ".sh"

def get_script_path(name):
    return os.path.join(xconfig.SCRIPTS_DIR, name)

def get_script_list():
    """获取脚本列表"""
    dirname = xconfig.SCRIPTS_DIR
    shell_list = []
    if os.path.exists(dirname):
        for fname in os.listdir(dirname):
            fpath = os.path.join(dirname, fname)
            if os.path.isfile(fpath) and fpath.endswith(SCRIPT_EXT_LIST):
                shell_list.append(fname)
    return sorted(shell_list)

class SaveHandler:

    @xauth.login_required("admin")
    def POST(self):
        name = xutils.get_argument("name")
        content = xutils.get_argument("content")
        dirname = xconfig.SCRIPTS_DIR
        path = os.path.join(dirname, name)
        content = content.replace("\r", "")
        xutils.savetofile(path, content)
        raise web.seeother("/system/script/edit?name="+xutils.quote(name))

class DeleteHandler:

    @xauth.login_required("admin")
    def POST(self):
        name = xutils.get_argument("name")
        dirname = xconfig.SCRIPTS_DIR
        path = os.path.join(dirname, name)
        os.remove(path)
        raise web.seeother("/system/script")

class ExecuteHandler:

    @xauth.login_required("admin")
    def GET(self):
        return self.POST()

    @xauth.login_required("admin")
    def POST(self):
        name = xutils.get_argument("name")
        content = xutils.get_argument("content")
        arg_path = xutils.get_argument("path")
        if content != "" and content != None:
            dirname = xconfig.SCRIPTS_DIR
            path = os.path.join(dirname, name)
            content = content.replace("\r", "")
            old_content = xutils.readfile(path)
            if old_content != content:
                xutils.savetofile(path, content)
        # 必须调用exec_script因为可能没有保存过程
        ret = xutils.exec_script(name, vars = dict(path=arg_path))
        return dict(code="success", message="", data=ret)

class SearchHandler:

    @xauth.login_required("admin")
    def GET(self):
        name = xutils.get_argument("name", "")
        list = [x for x in get_script_list() if x.find(name) >= 0]
        return xtemplate.render(template_file, shell_list = list, name=name)

class ListHandler:

    @xauth.login_required("admin")
    def GET(self):
        op    = xutils.get_argument("op")
        name  = xutils.get_argument("name", "")
        error = xutils.get_argument("error", "")
        dirname = xconfig.SCRIPTS_DIR

        content = ""
        if op == "edit":
            content = xutils.readfile(os.path.join(dirname, name))
        if op == "add" and name != "":
            path = os.path.join(dirname, name)
            basename, ext = os.path.splitext(name)
            if ext not in SCRIPT_EXT_LIST:
                name = basename + get_default_shell_ext()
                path = os.path.join(dirname, name)
            if os.path.exists(path):
                raise web.seeother(xutils.quote_unicode("/system/script_admin?error=%r已存在" % name))
            xutils.touch(path)

        shell_list = get_script_list()
        return xtemplate.render(template_file, 
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

        return xtemplate.render(template_file, 
            op = "edit",
            name = name,
            content = content,
            shell_list = [],
            error = error)

class RenameHandler:

    @xauth.login_required("admin")
    def POST(self):
        oldname = xutils.get_argument("oldname")
        newname = xutils.get_argument("newname")
        oldpath = get_script_path(oldname)
        newpath = get_script_path(newname)
        if not os.path.exists(oldpath):
            return dict(code="fail", message="源文件不存在")
        if os.path.exists(newpath):
            return dict(code="fail", message="目标文件已存在")
        try:
            os.rename(oldpath, newpath)
            return dict(code="success")
        except Exception as e:
            return dict(code="fail", message=str(e))

xurls = (
    r"/system/script", ListHandler,
    r"/system/script_admin", ListHandler,

    r"/system/script/search", SearchHandler,

    r"/system/script_admin/edit", EditHandler,
    r"/system/script/edit", EditHandler,
    
    r"/system/script_admin/save", SaveHandler,
    r"/system/script/save", SaveHandler,

    r"/system/script_admin/execute", ExecuteHandler,
    r"/system/script/execute", ExecuteHandler,

    r"/system/script_admin/delete", DeleteHandler,
    r"/system/script/delete", DeleteHandler,
    r"/system/script/rename", RenameHandler,
)


