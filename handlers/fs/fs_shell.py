# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/06/24 14:27:15
# @modified 2018/06/24 21:33:02
import web
import os
import xconfig
import xutils
import xtemplate
import sys
import xauth
from xutils import ziputil, fsutil


class ShellHandler:

    @xauth.login_required("admin")
    def GET(self):
        path = xutils.get_argument("path")
        path = xutils.get_real_path(path)
        error = ""
        if path == None or path == "":
            path = xconfig.DATA_DIR
        if not os.path.exists(path):
            error = "[%s] not exits!" % path
            filelist = []
        else:
            filelist = fsutil.list_files(path)
        return xtemplate.render("fs/fs_shell.html", 
            error = error,
            path = path, 
            filelist = filelist)

xurls = (
    r"/fs_shell", ShellHandler
)