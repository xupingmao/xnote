# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/06/23 02:07:02
# @modified 2019/07/30 00:59:35
import os
import web
import xutils
import xtemplate
import xauth
import xconfig
from xutils import fsutil

class SidebarHandler:

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
        return xtemplate.render("fs/fs_sidebar.html", 
            error = error,
            path = path, 
            filelist = filelist)

class PreviewHandler:

    @xauth.login_required("admin")
    def GET(self):
        # TODO 使用文件扩展
        path = xutils.get_argument("path")
        path = xutils.get_real_path(path)
        if xutils.is_img_file(path):
            return """<html><img style="width: 100%%;" src="/fs/%s"></html>""" % path
        if xutils.is_text_file(path):
            raise web.seeother("/code/edit?path=%s&embed=true" % xutils.quote_unicode(path))
        raise web.seeother("/fs_plugins?path=%s" % xutils.quote_unicode(path))

xurls = (
    r"/fs_sidebar", SidebarHandler,
    r"/fs_preview", PreviewHandler,
)