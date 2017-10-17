# encoding=utf-8
import os
import time

import xutils
from handlers.base import *

def is_img(filename):
    name, ext = os.path.splitext(filename)
    return ext.lower() in (".gif", ".png", ".jpg", ".jpeg", ".bmp")

def get_link(filename, webpath):
    if is_img(filename):
        return "![%s](%s)" % (filename, webpath)
    return "[%s](%s)" % (filename, webpath)

def print_env():
    for key in web.ctx.env:
        print(" - - %-20s = %s" % (key, web.ctx.env.get(key)))

class handler:

    def POST(self):
        file = xutils.get_argument("file", {})
        type = xutils.get_argument("type", "normal")
        prefix = xutils.get_argument("prefix", "")
        filepath = ""
        filename = ""
        # print_env()
        if not hasattr(file, "filename") or file.filename == "":
            return xtemplate.render("file/upload_file.html", filepath = filepath, filename = filename)
        filename = file.filename
        # Fix IE HMTL5 API拿到了全路径
        filename = os.path.basename(filename)
        quoted_filename = xutils.quote(filename)
        filepath, webpath = get_upload_file_path(quoted_filename, prefix=prefix)
        with open(filepath, "wb") as fout:
            # fout.write(x.file.file.read())
            for chunk in file.file:
                fout.write(chunk)

        if type == "html5":
            return dict(success=True, message="上传成功", link=get_link(filename, webpath))
        return xtemplate.render("file/upload_file.html", 
            filepath = webpath, 
            filename = filename, 
            is_img=is_img(filename))


        