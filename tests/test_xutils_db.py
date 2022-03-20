# -*- coding:utf-8 -*-
# @author mark
# @since 2022/03/20 19:01:28
# @modified 2022/03/20 21:36:21
# @filename test_xutils_db.py

import sys
import os
sys.path.insert(1, "lib")
sys.path.insert(1, "core")
import unittest
import json
import web
import six
import xmanager
import xutils
import xtemplate
import xconfig
import xtables
from xutils import u, dbutil

# cannot perform relative import
try:
    import test_base
except ImportError:
    from tests import test_base

app          = test_base.init()
json_request = test_base.json_request
request_html = test_base.request_html
BaseTestCase = test_base.BaseTestCase


class MockedWriteBatch:

    def __init__(self):
        self._puts = dict()
        self._deletes = set()

    def put(self, key, value):
        self._deletes.discard(key)
        self._puts[key] = value

    def delete(self, key):
        self._puts.pop(key, None)
        self._deletes.add(key)

def run_range_test_from_None(test, db):
    for key in db.RangeIter(include_value = False):
        db.Delete(key)

    db.Put(b"test5:1", b"value1")
    db.Put(b"test5:5", b"value5")
    db.Put(b"test5:2", b"value2")
    db.Put(b"test6:1", b"user1")
    db.Put(b"test6:2", b"user2")

    data_list = list(db.RangeIter(key_to = b"test5:\xff"))

    test.assertEqual(3, len(data_list))
    test.assertEqual((b"test5:1", b"value1"), data_list[0])
    test.assertEqual((b"test5:2", b"value2"), data_list[1])
    test.assertEqual((b"test5:5", b"value5"), data_list[2])

def run_range_test(test, db):
    data_list = list(db.RangeIter(key_from = b"test5:", 
        key_to = b"test5:\xff", 
        include_value = True))

    test.assertEqual(3, len(data_list))
    test.assertEqual((b"test5:1", b"value1"), data_list[0])
    test.assertEqual((b"test5:2", b"value2"), data_list[1])
    test.assertEqual((b"test5:5", b"value5"), data_list[2])

    data_list = list(db.RangeIter(key_from = b"test6:", 
        key_to = b"test6:\xff", 
        include_value = True,
        reverse = True))

    test.assertEqual(2, len(data_list))
    test.assertEqual((b"test6:2", b"user2"), data_list[0])
    test.assertEqual((b"test6:1", b"user1"), data_list[1])

    # 只返回Key的
    data_list = list(db.RangeIter(key_from = b"test6:", 
        key_to = b"test6:\xff", 
        include_value = False,
        reverse = True))
    test.assertEqual(2, len(data_list))
    test.assertEqual(b"test6:2", data_list[0])
    test.assertEqual(b"test6:1", data_list[1])

    # 统计所有的数量
    all_list = list(db.RangeIter())
    test.assertEqual(5, len(all_list))

    all_list_only_key = list(db.RangeIter(include_value = False))
    test.assertEqual(5, len(all_list_only_key))

    db.Put(b"test8:1", b"value8_1")

    # 一个都不匹配的迭代
    empty_iter_list = list(db.RangeIter(key_from = b"test7:", key_to=b"test7:\xff"))
    test.assertEqual(0, len(empty_iter_list))

def run_test_db_engine(test, db):
    for key in db.RangeIter(include_value = False):
        db.Delete(key)

    db.Put(b"key", b"value")
    test.assertEqual(b"value", db.Get(b"key"))
    db.Delete(b"key")
    test.assertEqual(None, db.Get(b"key"))

    db.Put(b"key_to_delete", b"delete")

    batch = MockedWriteBatch()
    batch.put(b"test5:1", b"value1")
    batch.put(b"test5:5", b"value5")
    batch.put(b"test5:2", b"value2")
    batch.put(b"test6:1", b"user1")
    batch.put(b"test6:2", b"user2")
    batch.delete(b"key_to_delete")

    db.Write(batch)

    test.assertEqual(b"value1", db.Get(b"test5:1"))
    test.assertEqual(None, db.Get(b"key_to_delete"))

    run_range_test(test, db)

    run_range_test_from_None(test, db)


def run_snapshot_test(test, db):
    # TODO 快照测试
    pass

class TestMain(BaseTestCase):

    def test_dbutil_lmdb(self):
        from xutils.db.driver_lmdb import LmdbKV
        db_dir = os.path.join(xconfig.DB_DIR, "lmdb")
        # 初始化一个5M的数据库
        db = LmdbKV(db_dir, map_size = 1024 * 1024 * 5)
        run_test_db_engine(self, db)

    def test_dbutil_sqlite(self):
        from xutils.db.driver_sqlite import SqliteKV
        db_file = os.path.join(xconfig.DB_DIR, "sqlite", "test.db")
        db = SqliteKV(db_file)
        run_test_db_engine(self, db)
        
    def test_dbutil_leveldbpy(self):
        if not xutils.is_windows():
            return
        from xutils.db.driver_leveldbpy import LevelDBProxy
        db_dir = os.path.join(xconfig.DB_DIR, "leveldbpy_test")
        db = LevelDBProxy(db_dir)
        run_test_db_engine(self, db)
        run_snapshot_test(self, db.CreateSnapshot())


    def test_dbutil_leveldb(self):
        if xutils.is_windows():
            return
        from xutils.db.driver_leveldb import LevelDBImpl
        db_dir = os.path.join(xconfig.DB_DIR, "leveldb_test")
        db = LevelDBImpl(db_dir)
        run_test_db_engine(self, db)
        run_snapshot_test(self, db.CreateSnapshot())