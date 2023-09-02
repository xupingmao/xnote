# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/06/23 02:07:02
# @modified 2020/03/21 17:28:19
import os
import web
import xutils
import xtemplate
import xauth
import xconfig
from xutils import fsutil

preview_dict = xconfig.load_config_as_dict("./config/file/preview.properties")

class SidebarHandler:

    @xauth.login_required("admin")
    def GET(self):
        path = xutils.get_argument("path", "")
        path = xutils.get_real_path(path)
        error = ""
        if path == None or path == "":
            path = xconfig.DATA_DIR
        if not os.path.exists(path):
            error = "[%s] not exits!" % path
            filelist = []
        else:
            filelist = fsutil.list_files(path)
        return xtemplate.render("fs/page/fs_sidebar.html", 
            error = error,
            path = path, 
            filelist = filelist)

class PreviewHandler:

    @xauth.login_required("admin")
    def GET(self):
        # TODO 使用文件扩展
        path = xutils.get_argument_str("path", "")
        embed = xutils.get_argument_str("embed", "true")

        path = xutils.get_real_path(path)
        path = path.replace("\\", "/")
        encoded_path = xutils.encode_uri_component(path)
        _, ext = os.path.splitext(path)
        ext = ext.lower()
        
        open_url = preview_dict.get(ext)
        if open_url != None and open_url != "":
            quoted_path = xutils.quote(path)
            return web.seeother(open_url.format(path=encoded_path, quoted_path=quoted_path, embed = embed))

        if xutils.is_img_file(path):
            return """<html><img style="width: 100%%;" src="/fs/~%s"></html>""" % xutils.quote(path)
        
        if xutils.is_text_file(path):
            raise web.seeother("/code/edit?path={path}&embed={embed}".format(path=encoded_path, embed=embed))

        raise web.seeother("/fs_hex?path={path}&embed={embed}".format(path=encoded_path, embed=embed))


class ViewHandler:

    @xauth.login_required("admin")
    def GET(self):
        fpath = xutils.get_argument_str("path")
        fpath = fpath.replace("\\", "/")
        
        basename, ext = os.path.splitext(fpath)
        encoded_fpath = xutils.encode_uri_component(fpath)

        if ext == ".txt":
            raise web.found("/fs_text?path=%s" % encoded_fpath)

        if ext in (".html", ".htm"):
            raise web.found("/fs/%s" % encoded_fpath)

        if ext in (".md", ".csv"):
            raise web.found("/code/preview?path=%s" % encoded_fpath)

        if ext in (".key", ".numbers"):
            os.system("open %r" % fpath)
            parent_fpath = os.path.abspath(os.path.dirname(fpath))
            encoded_parent = xutils.encode_uri_component(parent_fpath)
            raise web.found("/fs/~%s" % encoded_parent)

        if ext == ".db":
            raise web.found("/system/sqlite?path=%s" % encoded_fpath)

        if xutils.is_text_file(fpath) or xutils.is_code_file(fpath):
            raise web.found("/code/edit?path=%s" % encoded_fpath)

        raise web.found("/fs/~%s" % encoded_fpath)

class EditHandler:

    @xauth.login_required("admin")
    def GET(self):
        fpath = xutils.get_argument_str("path")
        basename, ext = os.path.splitext(fpath)
        encoded_fpath = xutils.encode_uri_component(fpath)

        if xutils.is_text_file(fpath):
            raise web.found("/code/edit?path=%s" % encoded_fpath)

        raise web.found("/fs_hex?path=%s" % encoded_fpath)


xurls = (
    r"/fs_sidebar", SidebarHandler,
    r"/fs_preview", PreviewHandler,
    r"/fs_view",   ViewHandler,
    r"/fs_edit",   EditHandler,
)