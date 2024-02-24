# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-14 12:31:02
@LastEditors  : xupingmao
@LastEditTime : 2024-02-24 15:25:06
@FilePath     : /xnote/handlers/system/db_index.py
@Description  : 数据库索引管理
"""

from web.utils import Storage
from xnote.core import xauth
from xnote.core import xtemplate, xconfig
from xutils import dbutil
import xutils

class TableIndex:

    def __init__(self, table_name, index_names):
        self.table_name = table_name
        self.index_names = index_names
        
class TableInfoVO:
    
    def __init__(self, table_name="", index_name=""):
        self.table_name = table_name
        self.table_url = ""
        self.index_name = index_name
        self.index_url = ""
        self.index_count = 0
    
    @staticmethod
    def from_table_info(table_info: dbutil.TableInfo):
        if table_info.index_db is None:
            raise Exception("index_db is None")
        
        result = TableInfoVO()
        result.table_name = table_info.name
        result.table_url = xconfig.WebConfig.server_home + f"/system/db_scan?prefix={table_info.name}&reverse=true"
        result.index_name = table_info.index_db.table_name
        result.index_url = xconfig.WebConfig.server_home + f"/system/sqldb_detail?name={result.index_name}"
        result.index_count = table_info.index_db.count()
        return result

def count_index(table_name, index_name):
    index_table_name = dbutil.get_index_table_name(table_name, index_name)
    return dbutil.count_table(index_table_name, use_cache=True)

def count_table(table_name):
    return dbutil.count_table(table_name, use_cache=True)

class IndexHandler:

    @xauth.login_required("admin")
    def GET(self):
        
        p2 = xutils.get_argument_str("p2")
        if p2 == "index_v2":
            return self.get_index_v2()
        return self.get_index_v1()
    
    def get_index_v2(self):
        table_list = []
        
        for table_name in dbutil.get_table_names():
            table_info = dbutil.get_table_info(table_name)
            assert table_info != None
            if table_info.is_deleted:
                continue
            index_db = table_info.index_db
            if index_db != None:
                info = TableInfoVO.from_table_info(table_info)
                table_list.append(info)

        kw = Storage()
        kw.table_list = table_list

        return xtemplate.render("system/page/db/db_index_v2.html", **kw)

    def get_index_v1(self):
        index_list = []
        
        for table_name in dbutil.get_table_names():
            table_info = dbutil.get_table_info(table_name)
            assert table_info != None
            if table_info.is_deleted:
                continue
            index_names = dbutil.get_table_index_names(table_name)
            if len(index_names) > 0:
                index_list.append(TableIndex(table_name, index_names))

        kw = Storage()
        kw.index_list = index_list
        kw.count_index = count_index
        kw.count_table = count_table
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
            return dict(code = "fail", message = "重建索引异常")
            
        return dict(code = "success")


xurls = (
    r"/system/db_index", IndexHandler
)