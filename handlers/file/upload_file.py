# encoding=utf-8
import os
import time

from handlers.base import *

def is_img(filename):
    name, ext = os.path.splitext(filename)
    return ext.lower() in (".gif", ".png", ".jpg", ".jpeg", ".bmp")

class handler(BaseHandler):

    def execute(self):
        x = web.input(file = {})
        filepath = ""
        filename = ""
        file = x.file

        if not hasattr(file, "filename") or file.filename == "":
            self.render("file/upload_file.html", filepath = filepath, filename = filename)
            return
        filename = file.filename
        filepath, webpath = get_upload_file_path(file.filename)
        with open(filepath, "wb") as fout:
            # fout.write(x.file.file.read())
            for chunk in file.file:
                fout.write(chunk)
        self.render("file/upload_file.html", 
            filepath = webpath, 
            filename = filename, 
            is_img=is_img(filename))