# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/06
# 

"""Description here"""

import os
import web
import xutils
import config
import xtemplate
import zipfile

class FileInfo:

    def __init__(self, name, parent):
        self.name = name
        self.path = os.path.join(parent, name)
        self.app_name, ext = os.path.splitext(name)
        self.size = xutils.get_file_size(self.path)

class handler:

    def GET(self):
        parent = config.APP_DIR
        xutils.makedirs(parent)
        app_list = []
        for fname in os.listdir(parent):
            fpath = os.path.join(parent, fname)
            if fname.endswith(".zip"):
                app_list.append(FileInfo(fname, parent))
        return xtemplate.render("system/upload_app.html", 
            app_list = app_list)

    def POST(self):
        file = web.input(file={}).file
        filename = file.filename
        parent = config.APP_DIR

        filepath = os.path.join(parent, filename)
        with open(filepath, "wb") as fp:
            for chunk in file.file:
                fp.write(chunk)
        # 解压文件

        basename, ext = os.path.splitext(filename)
        app_dir = os.path.join(parent, basename)

        # 删除旧文件
        if os.path.exists(app_dir):
            xutils.remove(app_dir)
        # mode只有'r', 'w', 'a'
        zf = zipfile.ZipFile(filepath, "r")
        zf.extractall(app_dir)
        return self.GET()

