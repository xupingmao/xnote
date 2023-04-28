# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-04-28 21:04:36
@LastEditors  : xupingmao
@LastEditTime : 2023-04-28 22:06:41
@FilePath     : /xnote/tests/test_xutils_sqldb.py
@Description  : 描述
"""

from . import test_base
from xutils.sqldb import SqliteTableManager, TableProxy
import xconfig
import os
import web.db

app = test_base.init()

class TestMain(test_base.BaseTestCase):

    def clear_table(self, table: TableProxy):
        table.delete(where = "1=1")

    def test_db_example(self):
        dbpath = os.path.join(xconfig.DB_DIR, "test.db")
        with SqliteTableManager("test", dbpath = dbpath) as table:
            table.add_column("name", "text")
            table.add_column("age", "int")

        db = web.db.SqliteDB(db = dbpath)
        table = TableProxy(db, "test")
        self.clear_table(table)
        
        table.insert(name = "test-1", age = 10)
        table.insert(name = "test-2", age = 30)

        age10 = table.select_first(where = dict(age=10))
        self.assertEqual("test-1", age10.name)


    def test_mysql_example(self):
        pass
    
