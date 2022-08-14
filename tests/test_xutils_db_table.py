# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-08-14 17:17:50
@LastEditors  : xupingmao
@LastEditTime : 2022-08-14 17:33:09
@FilePath     : /xnote/tests/test_xutils_db_table.py
@Description  : table测试
"""



from .a import *
from xutils import Storage
from xutils import dbutil
from xutils import textutil
from xutils import netutil
from xutils.db.binlog import BinLog
from xutils.db.dbutil_deque import DequeTable

import os
import threading
import sqlite3
import time
import xutils
import xconfig
import json

from . import test_base

app = test_base.init()
json_request = test_base.json_request
request_html = test_base.request_html
BaseTestCase = test_base.BaseTestCase

dbutil.register_table("test", "测试数据库")
dbutil.register_table_index("test", "name")
dbutil.register_table_index("test", "age")

dbutil.register_table("test_user_db1", "测试数据库用户版v1")

dbutil.register_table("test_user_db", "测试数据库用户版", check_user=True)
dbutil.register_table_user_attr("test_user_db", "user")



class TestMain(BaseTestCase):

    def test_table_with_user_in_class(self):
        db1 = dbutil.get_table("test_user_db1", user_name="Ada")
        db2 = dbutil.get_table("test_user_db1", user_name="Bob")

        for item in db1.iter(limit=-1):
            db1.delete(item)
        for item in db2.iter(limit=-1):
            db2.delete(item)

        db1.insert(dict(user="Ada", prop="key1", prop_value="222"), id_type = "auto_increment")
        db1.insert(dict(user="Ada", prop="key2", prop_value="333"), id_type = "auto_increment")

        db2.insert(dict(user="Bob", prop="key3", prop_value="111"), id_type = "auto_increment")
        db2.insert(dict(user="Bob", prop="key4", prop_value="111"), id_type = "auto_increment")

        result1 = db1.list(limit=-1)

        self.assertTrue(len(result1) > 0)

        first = db1.get_first()
        self.assertEqual("key1", first.prop)
        self.assertEqual("test_user_db1:Ada:"+first._id, first._key)

        last = db1.get_last()
        self.assertEqual("key2", last.prop)

        # 通过key进行更新和查询
        first.job = "painter"
        db1.update_by_key(first._key, first)
        first = db1.get_by_key(first._key)
        self.assertEqual("painter", first.job)

        # 通过ID更新和查询
        first.job = "teacher"
        db1.update_by_id(first._id, first)
        first = db1.get_by_id(first._id)
        self.assertEqual("teacher", first.job)

        # 查询
        self.assertIsNone(db1.get_by_key(""))
        self.assertIsNone(db1.get_by_key("test_user_db1:Ada:not_exists"))

        # 删除
        first = db1.get_first()
        db1.delete_by_id(first._id)

        self.assertIsNone(db1.get_by_id(first._id))
        self.assertEqual(1, db1.count())

    def test_table_with_user_in_param(self):
        db = dbutil.get_table("test_user_db")

        for item in db.iter():
            db.delete(item)

        db.insert(dict(user="Ada", prop="key1", prop_value="222"))
        db.insert(dict(user="Ada", prop="key2", prop_value="333"))
        db.insert_by_user("Bob", dict(
            user="Bob", prop="key3", prop_value="111"))
        db.insert_by_user("Bob", dict(
            user="Bob", prop="key4", prop_value="111"))

        result1 = db.list(limit=-1, user_name="Ada")
        result2 = db.list_by_func("Ada", limit=-1)

        self.assertTrue(len(result1) > 0)
        self.assertEqual(result1, result2)
        self.assertEqual(2, len(result1))
        self.assertEqual(2, len(db.list_by_user("Ada")))

        first = db.get_first()
        self.assertEqual("key1", first.prop)

        last = db.get_last()
        self.assertEqual("key4", last.prop)

        # 通过key进行更新和查询
        first.job = "painter"
        db.update_by_key(first._key, first)
        first = db.get_by_key(first._key)
        self.assertEqual("painter", first.job)

        # 通过ID更新和查询
        first.job = "teacher"
        db.update_by_id(first._id, first, user_name=first.user)
        first = db.get_by_id(first._id, user_name=first.user)
        self.assertEqual("teacher", first.job)

