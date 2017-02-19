#encoding=utf-8
import os
import web
import xtemplate

class handler:
    
    __url__ = "/fs_preview"

    def GET(self):
        args = web.input()
        path = args.path
        files = os.listdir(path)
        files = list(filter(lambda name: name.lower().endswith(".jpg"), files))
        return xtemplate.render("fs/preview.html", 
            dirname = path,
            filelist = files,
            os = os)
