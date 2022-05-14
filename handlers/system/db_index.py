# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-14 12:31:02
@LastEditors  : xupingmao
@LastEditTime : 2022-05-14 17:39:32
@FilePath     : /xnote/handlers/system/db_index.py
@Description  : 数据库索引管理
"""

from handlers import message
from web.utils import Storage
import xauth
import xtemplate
from xutils import dbutil
import xutils

class TableIndex:

    def __init__(self, table_name, index_names):
        self.table_name = table_name
        self.index_names = index_names

def count_index(table_name, index_name):
    index_table_name = dbutil.get_index_table_name(table_name, index_name)
    return dbutil.count_table(index_table_name)

class IndexHandler:

    @xauth.login_required("admin")
    def GET(self):
        index_list = []
        
        for table_name in dbutil.get_table_names():
            index_names = dbutil.get_table_index_names(table_name)
            if len(index_names) > 0:
                index_list.append(TableIndex(table_name, index_names))

        kw = Storage()
        kw.index_list = index_list
        kw.count_index = count_index
        kw.count_table = dbutil.count_table
        kw.get_index_table_name = dbutil.get_index_table_name

        return xtemplate.render("system/page/db/db_index.html", **kw)
    
    @xauth.login_required("admin")
    def POST(self):
        action = xutils.get_argument("action", "")
        if action == "rebuild":
            return self.rebuild_index()
        return dict(code = "404", message = "未知操作")
    
    def rebuild_index(self):
        table_name = xutils.get_argument("table_name", "")

        db = dbutil.get_table(table_name)
        try:
            db.repair_index()
        except:
            xutils.print_exc()
            return dict(code = "fail", message = "重建索引异常")
            
        return dict(code = "success")


xurls = (
    r"/system/db_index", IndexHandler
)