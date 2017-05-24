# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017
# 

"""Description here"""
import time

from handlers.base import *
from .dao import FileDO
from . import dao

import xauth
import xutils

class handler(BaseHandler):

    def execute(self):
        name = xutils.get_argument("name", "")
        tags = xutils.get_argument("tags", "")
        key  = xutils.get_argument("key", "")
        type = xutils.get_argument("type", "post")
        parent_id = xutils.get_argument("parent_id", 0, type=int)

        if key == "":
            key = time.strftime("%Y-%m-%d")

        file = FileDO(name)
        file.atime   = dateutil.get_seconds()
        file.satime  = dateutil.format_time()
        file.mtime   = dateutil.get_seconds()
        file.smtime  = dateutil.format_time()
        file.ctime   = dateutil.get_seconds()
        file.sctime  = dateutil.format_time()
        file.creator = xauth.get_current_user()["name"]
        # 默认私有
        file.groups    = file.creator
        file.parent_id = parent_id
        file.type      = type
        file.content   = ""

        error = ""
        try:
            if name != '':
                f = dao.get_by_name(name)
                if f != None:
                    key = name
                    raise Exception("%s 已存在" % name)
                f = dao.insert(file)
                inserted = dao.get_by_name(name)
                raise web.seeother("/file/view?id={}".format(inserted.id))
        except Exception as e:
            xutils.print_stacktrace()
            error = e
        self.render("file/add.html", key = "", name = key, tags = tags, error=error)

