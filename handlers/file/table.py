# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/08
# 

"""Description here"""

import os
import re

import web
import xtemplate
import web.db as db

import xutils
import xconfig
import xtables
from util import dateutil
from util import fsutil

class TableView(object):
    """docstring for handler"""
    
    def GET(self):
        id = xutils.get_argument("id", type=int)
        db = xtables.get_file_table()
        return db.select_one(where={"id":id})

class TableSave:

    def POST(self):
        id = xutils.get_argument("id", type=int)
        content = xutils.get_argument("content")
        name = xutils.get_argument("name")
        db = xtables.get_file_table()
        # record = db.select_one(where={"id": id})
        if name != "":
            db.update(where={"id":id}, content=content,name=name)
        else:
            db.update(where={"id":id}, content=content)
        return dict(code="success")

xurls = (
    r"/file/table", TableView,
    r"/file/table/save", TableSave
)