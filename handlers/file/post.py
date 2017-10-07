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
import xconfig

from handlers.base import get_upload_file_path
from util import dateutil
from util import fsutil

from . import dao

config = xconfig

class PostView(object):
    """docstring for handler"""
    
    def GET(self):
        args = web.input()
        id = int(args.id)
        file = dao.get_by_id(id)
        if file.content != None:
            file.content = xutils.html_escape(file.content, quote=False);
            # \xad (Soft hyphen), 用来处理断句的
            file.content = file.content.replace('\xad', '\n')
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
        dao.visit_by_id(id)

        return xtemplate.render("file/view.html",
            op = "view",
            file = file,
            file_type = "post")

class PostEdit:

    def GET(self):
        args = web.input()
        id = int(args.id)
        file = dao.get_by_id(id)
        if file.content == None:
            file.content = ""
        file.content = file.content.replace('\xad', '\n')
        rows = file.content.count("\n")+5
        rows = max(rows, 20)
        return xtemplate.render("file/view.html", 
            op="edit", 
            file=file,
            rows = rows,
            file_type = "post")

    def POST(self):
        # 一定要加file={}
        # 参考web.utils.storify
        args = web.input(file={}, public="off")
        id = int(args.id)
        file = dao.get_by_id(id)
        version = int(args.version)
        name    = xutils.get_argument("name")

        content = args.content
        groups = file.creator
        if args.public == "on":
            groups = "*"

        if hasattr(args.file, "filename") and args.file.filename!="":
            filename = args.file.filename
            filepath, webpath = get_upload_file_path(args.file.filename)
            with open(filepath, "wb") as fout:
                # fout.write(x.file.file.read())
                for chunk in args.file.file:
                    fout.write(chunk)
            content = content + "\n[img src=\"{}\"img]".format(webpath)

        rowcount = dao.update(where=dict(id=id, version=version), 
            groups = groups, type="post", size=len(content), content=content, name=name)
        if rowcount > 0:
            raise web.seeother("/file/view?id={}".format(id))
        else:
            cur_version = file.version
            file.content = content
            file.version = version
            
            rows = content.count("\n")+5
            rows = max(rows, 20)

            return xtemplate.render("file/post.html",
                op = "edit",
                error="version冲突,version={},最新version={}".format(version, cur_version),
                file=file,
                rows=rows)

        
class PostDel:
    def GET(self):
        args = web.input()
        id = int(args.id)
        dao.delete_by_id(id)
        raise web.seeother("/")

xurls = ("/file/post", PostView, 
        "/file/post/edit", PostEdit, 
        "/file/post/del", PostDel)


