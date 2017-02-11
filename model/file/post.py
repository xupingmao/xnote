# encoding=utf-8
# filename post.py

import os
import web
import xtemplate
import web.db as db

import xutils

from util import dateutil
from util import fsutil

class PostView(object):
    """docstring for handler"""
    
    def GET(self):
        args = web.input()
        id = int(args.id)
        file_db = db.SqliteDB(db="db/data.db")
        file = file_db.select("file", where={"id": id})[0]
        if file.content != None:
            file.content = xutils.html_escape(file.content, quote=False)\
                .replace("[[img", "<img")\
                .replace("]]", ">")

        return xtemplate.render("file/post.html",
            op = "view",
            file = file)

class PostEdit:
    def create_file_name(self, filename):
        date = dateutil.format_date(fmt="%Y/%m")
        newfilename = "static/img/" + date + "/" + filename
        fsutil.check_create_dirs("static/img/"+date)
        while os.path.exists(newfilename):
            name, ext = os.path.splitext(newfilename)
            newfilename = name + "1" + ext
        return newfilename

    def GET(self):
        args = web.input()
        id = int(args.id)
        file_db = db.SqliteDB(db="db/data.db")
        file = file_db.select("file", where={"id": id})[0]
        return xtemplate.render("file/post.html", 
            op="eidt", 
            file=file)

    def POST(self):
        # 一定要加file={}
        args = web.input(file={}, public=None)
        id = int(args.id)
        file_db = db.SqliteDB(db="db/data.db")
        file = file_db.select("file", where={"id": id})[0]
        file.content = args.content
        file.smtime = dateutil.format_time()
        file.name = args.name
        if args.public == "on":
            file.groups = "*"
        else:
            file.groups = file.creator
        if hasattr(args.file, "filename") and args.file.filename!="":
            filename = args.file.filename
            filepath = self.create_file_name(args.file.filename)
            fout = open(filepath, "wb")
            # fout.write(x.file.file.read())
            for chunk in args.file.file:
                fout.write(chunk)
            fout.close()
            file.content = file.content + "\n[[img src=\"/{}\"]]".format(filepath)

        file_db.update("file", where={"id": id}, vars=["content"], **file)
        raise web.seeother("/file/post?id={}".format(id))
        
xurls = ("/file/post", PostView, "/file/post/edit", PostEdit)

