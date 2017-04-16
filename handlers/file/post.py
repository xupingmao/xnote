# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/03
# 

"""Description here"""

import os
import re

import web
import xtemplate
import web.db as db

import xutils
import config

from handlers.base import get_upload_img_path
from util import dateutil
from util import fsutil

def get_file_db():
    return db.SqliteDB(db=config.DB_PATH)

class PostView(object):
    """docstring for handler"""
    
    def GET(self):
        args = web.input()
        id = int(args.id)
        file_db = get_file_db()
        file = file_db.select("file", where={"id": id})[0]
        if file.content != None:
            file.content = xutils.html_escape(file.content, quote=False);
            # file.content = file.content.replace(" ", "&nbsp;")
            file.content = re.sub(r"https?://[^\s]+", '<a href="\\g<0>">\\g<0></a>', file.content)
            file.content = file.content.replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;")
            file.content = file.content.replace("\n", "<br/>")
            # 处理图片
            file.content = file.content.replace("[img", "<p style=\"text-align:center;\"><img")
            file.content = file.content.replace("img]", "></p>")
            # 处理空格
            file.content = file.content.replace(" ", "&nbsp;")
            # 允许安全的HTML标签
            file.content = re.sub(r"\<(a|img|p)&nbsp;", "<\\g<1> ", file.content)

        # 统计访问次数，不考虑并发
        file_db.update("file", where={"id": id}, visited_cnt=file.visited_cnt+1)

        return xtemplate.render("file/post.html",
            op = "view",
            file = file)

class PostEdit:

    def GET(self):
        args = web.input()
        id = int(args.id)
        file_db = get_file_db()
        file = file_db.select("file", where={"id": id})[0]
        if file.content == None:
            file.content = ""
        rows = file.content.count("\n")+5
        rows = max(rows, 20)
        return xtemplate.render("file/post.html", 
            op="eidt", 
            file=file,
            rows = rows)

    def POST(self):
        # 一定要加file={}
        # 参考web.utils.storify
        args = web.input(file={}, public="off")
        id = int(args.id)
        file_db = get_file_db()
        file = file_db.select("file", where={"id": id})[0]
        file.content = args.content
        file.smtime = dateutil.format_time()
        file.name = args.name
        file.type = "post"
        file.size = len(file.content)
        file.version = file.version + 1
        if args.public == "on":
            file.groups = "*"
        else:
            file.groups = file.creator
        if hasattr(args.file, "filename") and args.file.filename!="":
            filename = args.file.filename
            filepath, webpath = get_upload_img_path(args.file.filename)
            fout = open(filepath, "wb")
            # fout.write(x.file.file.read())
            for chunk in args.file.file:
                fout.write(chunk)
            fout.close()
            file.content = file.content + "\n[img src=\"{}\"img]".format(webpath)

        file_db.update("file", where={"id": id}, vars=None, **file)
        raise web.seeother("/file/post?id={}".format(id))
        
class PostDel:
    def GET(self):
        args = web.input()
        id = int(args.id)
        file_db = get_file_db()
        file_db.delete("file", where={"id": id})
        raise web.seeother("/")

xurls = ("/file/post", PostView, 
        "/file/post/edit", PostEdit, 
        "/file/post/del", PostDel)


