# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-04-29 18:57:21
@LastEditors  : xupingmao
@LastEditTime : 2023-05-20 22:45:02
@FilePath     : /xnote/tests/test_xutils_db_hash_table.py
@Description  : 描述
"""

from . import test_base
from xutils import dbutil, Storage

app = test_base.init()
dbutil.register_table("hash_test", "测试数据库")

class TestMain(test_base.BaseTestCase):

    def get_table(self):
        return dbutil.get_hash_table("hash_test")
    
    def drop_table(self):
        table = self.get_table()
        for key, value in table.iter(limit = -1):
            table.delete(key)

    def test_db_example(self):
        table = self.get_table()
        self.drop_table()
        
        table.put("x", 1)
        self.assertEqual(1, table.get("x"))
        self.assertEqual(1, table.count())
        self.assertEqual(("x", 1), table.first())
        self.assertEqual(("x", 1), table.last())
    
    def test_sub_table(self):
        table = self.get_table()
        self.drop_table()

        sub_table = table.sub_table("sub")
        sub_table.put("x", 1)

        self.assertEqual(1, dbutil.db_get("hash_test:sub:x"))

        sub_table.put("x", 2)
        self.assertEqual(2, dbutil.db_get("hash_test:sub:x"))

    def test_object(self):
        table = self.get_table()
        user_info = Storage()
        user_info.name = "admin"
        user_info.age  = 20
        user_info.email = "abc@test.com"
        table.put("admin", user_info)

        found = table.get("admin")
        self.assertEqual("admin", found.name)
        self.assertEqual(20, found.age)

        key, first = table.first(where=dict(age=20))
        self.assertEqual("admin", first.name)
        self.assertEqual(20, first.age)

