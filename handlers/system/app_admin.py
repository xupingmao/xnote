# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/06
# 

"""Description here"""

import os
import zipfile

import web
import xutils
import xconfig
import xtemplate

config = xconfig

class FileInfo:

    def __init__(self, name, parent):
        self.name = xutils.unquote(name)
        self.path = os.path.join(parent, name)
        self.app_name, ext = os.path.splitext(name)
        self.app_name = xutils.unquote(self.app_name)
        self.size = xutils.get_file_size(self.path)

class handler:

    def GET(self, error=""):
        parent = config.APP_DIR
        xutils.makedirs(parent)
        app_list = []
        for fname in os.listdir(parent):
            fpath = os.path.join(parent, fname)
            if fname.endswith(".zip"):
                app_list.append(FileInfo(fname, parent))
        return xtemplate.render("system/app_admin.html", 
            app_list = app_list, error = error, upload_path=os.path.abspath(xconfig.APP_DIR))

    def POST(self):
        file = web.input(file={}).file
        filename = file.filename
        parent = config.APP_DIR

        basename, ext = os.path.splitext(filename)
        if ext != ".zip":
            return self.GET("Expect zip file!")

        filepath = os.path.join(parent, filename)
        with open(filepath, "wb") as fp:
            for chunk in file.file:
                fp.write(chunk)
        # 解压文件

        basename, ext = os.path.splitext(filename)
        app_dir = os.path.join(parent, basename)
        error = ""

        try:
            # 删除旧文件
            if os.path.exists(app_dir):
                xutils.remove(app_dir)
            # mode只有'r', 'w', 'a'
            zf = zipfile.ZipFile(filepath, "r")
            zf.extractall(app_dir)
        except Exception as e:
            error = str(e)
        return self.GET(error)

class UnzipApp:
    def GET(self):
        parent = xconfig.APP_DIR
        name = xutils.get_argument("name")
        if name == "" or name is None:
            raise web.seeother("/system/app_admin")
        # name = xutils.unquote(name)
        name = xutils.quote_unicode(name)
        basename, ext = os.path.splitext(name)
        if ext != ".zip":
            raise web.seeother("/system/app_admin?error=EXPECT_ZIP")
        app_dir = os.path.join(parent, basename)
        filepath = os.path.join(parent, name)
        error = ""
        try:
            # 删除旧文件
            if os.path.exists(app_dir):
                xutils.remove(app_dir)
            # mode只有'r', 'w', 'a'
            zf = zipfile.ZipFile(filepath, "r")
            zf.extractall(app_dir)
        except Exception as e:
            error = str(e)
        raise web.seeother("/system/app_admin?error="+error)

xurls = (
    r"/system/upload_app", handler,
    r"/system/app_admin", handler,
    r"/system/app_admin/unzip", UnzipApp,
)


