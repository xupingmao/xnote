# -*- coding:utf-8 -*-
# @author mark
# @since 2022/03/20 19:01:28
# @modified 2022/04/17 13:58:29
# @filename test_xutils_db.py

from .a import *
from xutils import Storage
from xutils import dbutil
from xutils import textutil
from xutils import netutil
from xutils import logutil
from xutils.db.binlog import BinLog
from xutils.db.dbutil_deque import DequeTable
from xutils.db.encode import decode_id
from xutils import interfaces

import pdb
import logging
import os
import threading
import sqlite3
import time
import xutils
from xnote.core import xconfig
from xnote.core import xtables
import json
import web.db

from . import test_base

app = test_base.init()
json_request = test_base.json_request
request_html = test_base.request_html
BaseTestCase = test_base.BaseTestCase

db = dbutil.register_table("test", "测试数据库")
db.register_index("name")
db.register_index("age")

dbutil.register_table("test_user_db1", "测试数据库用户版v1")
dbutil.register_table("test_user_db", "测试数据库用户版", user_attr="user")
dbutil.register_table("sortedset_test", "sortedset测试", type="sorted_set")

BinLog.set_enabled(True)


class MockedWriteBatch(interfaces.BatchInterface):

    def __init__(self):
        self._puts = {}
        self._inserts = {}
        self._deletes = set()

    def put(self, key, value):
        self._deletes.discard(key)
        self._puts[key] = value

    def delete(self, key):
        self._puts.pop(key, None)
        self._deletes.add(key)
    
    def insert(self, key, value):
        self._deletes.discard(key)
        self._inserts[key] = value

def run_range_test_from_None(test, db):
    for key in db.RangeIter(include_value=False, key_from = b'', key_to = b'\xff'):
        db.Delete(key)
        print("Delete", key, db)

    db.Put(b"test5:1", b"value1")
    db.Put(b"test5:5", b"value5")
    db.Put(b"test5:2", b"value2")
    db.Put(b"test6:1", b"user1")
    db.Put(b"test6:2", b"user2")

    data_list = list(db.RangeIter(key_to=b"test5:\xff"))

    test.assertEqual(3, len(data_list))
    test.assertEqual((b"test5:1", b"value1"), data_list[0])
    test.assertEqual((b"test5:2", b"value2"), data_list[1])
    test.assertEqual((b"test5:5", b"value5"), data_list[2])


def run_range_test(test, db):
    data_list = list(db.RangeIter(key_from=b"test5:",
                                  key_to=b"test5:\xff",
                                  include_value=True))

    test.assertEqual(3, len(data_list))
    test.assertEqual((b"test5:1", b"value1"), data_list[0])
    test.assertEqual((b"test5:2", b"value2"), data_list[1])
    test.assertEqual((b"test5:5", b"value5"), data_list[2])

    data_list = list(db.RangeIter(key_from=b"test6:",
                                  key_to=b"test6:\xff",
                                  include_value=True,
                                  reverse=True))

    test.assertEqual(2, len(data_list))
    test.assertEqual((b"test6:2", b"user2"), data_list[0])
    test.assertEqual((b"test6:1", b"user1"), data_list[1])

    # 只返回Key的
    data_list = list(db.RangeIter(key_from=b"test6:",
                                  key_to=b"test6:\xff",
                                  include_value=False,
                                  reverse=True))

    if len(data_list) != 2:
        print(data_list)

    test.assertEqual(2, len(data_list))
    test.assertEqual(b"test6:2", data_list[0])
    test.assertEqual(b"test6:1", data_list[1])

    # 统计所有的数量
    all_list = list(db.RangeIter())
    print("[all_list]", all_list, db)
    test.assertEqual(5, len(all_list))

    all_list_only_key = list(db.RangeIter(include_value=False))
    test.assertEqual(5, len(all_list_only_key))

    db.Put(b"test8:1", b"value8_1")

    # 一个都不匹配的迭代
    empty_iter_list = list(db.RangeIter(
        key_from=b"test7:", key_to=b"test7:\xff"))
    test.assertEqual(0, len(empty_iter_list))

    data_list = list(db.RangeIter(include_value=False, reverse=True))
    print("data_list:", data_list)
    test.assertEqual(b"test8:1", data_list[0])

    data_list = list(db.RangeIter(include_value=False,
                     reverse=True, key_to=b"test6:3"))
    print("data_list:", data_list)
    test.assertEqual(b"test6:2", data_list[0])

def run_increase_test(test, db):
    assert isinstance(db, interfaces.DBInterface)
    counter_key = b'counter'
    db.Delete(counter_key)
    result = db.Increase(counter_key)
    assert result == 1
    result = db.Increase(counter_key)
    assert result == 2

def run_insert_test(test, db):
    assert isinstance(db, interfaces.DBInterface)
    insert_key = b'insert_test'
    value = b'value'

    db.Delete(insert_key)
    db.Insert(insert_key, value)
    
    try:
        db.Insert(insert_key, value)
        assert 1==2
    except Exception as e:
        xutils.print_exc()
        print("err:", str(e))
        is_sqlite_err = "UNIQUE constraint failed" in str(e)
        is_default_err = "Duplicate" in str(e) 
        assert is_sqlite_err or is_default_err
    
    try:
        batch = dbutil.create_write_batch(db_instance=db)
        batch.insert(insert_key.decode("utf-8"), value, check_table=False)
        batch.commit()
        assert 1==2
    except Exception as e:
        xutils.print_exc()
        print("err:", str(e))
        is_sqlite_err = "UNIQUE constraint failed" in str(e)
        is_default_err = "Duplicate" in str(e) 
        assert is_sqlite_err or is_default_err

def run_batch_test(test, db):
    assert isinstance(db, interfaces.DBInterface)
    kv_dict = {
        b"batch-test:1": b"1",
        b"batch-test:2": b"2",
    }
    keys = list(kv_dict.keys())
    db.BatchPut(kv_dict)
    result = db.BatchGet(keys)
    assert len(result) == 2
    assert result[b"batch-test:1"] == b"1"
    assert result[b"batch-test:2"] == b"2"

    db.BatchDelete(keys)
    assert db.Count(b"batch-test:", b"batch-test:\xff") == 0

def run_test_db_engine(test, db):
    # 等待异步任务完成
    logutil.wait_task_done()

    for key in db.RangeIter(include_value=False):
        db.Delete(key)
        # print("Delete", key, db)

    db.Put(b"key", b"value")
    test.assertEqual(b"value", db.Get(b"key"))

    # 第二次测试Update
    db.Put(b'key', b'value2')
    test.assertEqual(b'value2', db.Get(b'key'))

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

    run_batch_test(test, db)

    run_range_test(test, db)

    run_range_test_from_None(test, db)

    run_increase_test(test, db)

    run_insert_test(test, db)


def run_snapshot_test(test, db):
    # TODO 快照测试
    pass


def to_str_list(list):
    result = []
    for item in list:
        if isinstance(item, bytes):
            result.append(item.decode("utf8"))
        elif isinstance(item, str):
            result.append(item)
        else:
            raise Exception("invalid type: %s" % type(item))
    return result

class TestMain(BaseTestCase):

    def test_dbutil_lmdb(self):
        from xutils.db.driver_lmdb import LmdbKV
        db_dir = os.path.join(xconfig.DB_DIR, "lmdb")
        # 初始化一个5M的数据库
        db = LmdbKV(db_dir, map_size=1024 * 1024 * 5)
        run_test_db_engine(self, db)

    def test_dbutil_lmdb_enhanced(self):
        from xutils.db.driver_lmdb import LmdbEnhancedKV
        db_dir = os.path.join(xconfig.DB_DIR, "lmdb")
        # 初始化一个5M的数据库
        db = LmdbEnhancedKV(db_dir, map_size=1024 * 1024 * 5)
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

    def get_mysql_instance(self):
        host = os.environ.get("mysql_host")
        user = os.environ.get("mysql_user")
        password = os.environ.get("mysql_password", "")
        database = os.environ.get("mysql_database", "")

        print("host=%s, user=%s, password=%s" % (host, user, password))

        xconfig.DatabaseConfig.mysql_database = database
        db_instance = web.db.MySQLDB(host=host, user=user, pw = password, database=database)
        db_instance.dbname = "mysql"
        return db_instance

    def get_mysql_kv(self):
        from xutils.db.driver_mysql import MySQLKV
        db = MySQLKV(db_instance = self.get_mysql_instance())
        return db

    def test_dbutil_mysql(self):
        print("test_dbutil_mysql start...")
        skip_mysql_test = os.environ.get("skip_mysql_test")
        if skip_mysql_test == "True":
            print("skip mysql test")
            return
        
        db = self.get_mysql_kv()
        run_test_db_engine(self, db)
        
    def test_mysql_put_with_version(self):
        key = b"test_key"
        db = self.get_mysql_kv()
        db.Delete(key)
        value = b'value'
        value_2 = b'value-2'
        
        db.Put(key, value)
        _, version = db.get_with_version(key)
        assert version == 1
        
        db.Put(key, value)
        _, version = db.get_with_version(key)
        assert version == 2
        
        rowcount = db.put_with_version(key, value_2, version=1)
        assert rowcount == 0
        
        rowcount = db.put_with_version(key, value_2, version=2)
        assert rowcount == 1
        
        query_value = db.Get(key)
        assert query_value == value_2
        
        db.Delete(key)

    def test_ssdb_kv(self):
        if not xconfig.SystemConfig.get_bool("test_ssdb"):
            return
        
        from xutils.db.driver_ssdb import SSDBKV
        db = SSDBKV()
        run_test_db_engine(self, db)

    def test_dbutil_mysql_enhanced(self):
        print("test_dbutil_mysql_enhanced start...")
        from xutils.db.driver_mysql_enhance import EnhancedMySQLKV
        skip_mysql_test = os.environ.get("skip_mysql_test")
        if skip_mysql_test == "True":
            print("skip mysql test")
            return
                
        host = os.environ.get("mysql_host")
        user = os.environ.get("mysql_user")
        password = os.environ.get("mysql_password")
        database = os.environ.get("mysql_database")

        db_instance = web.db.MySQLDB(host=host, user=user, pw = password, database=database)
        db = EnhancedMySQLKV(db_instance=db_instance)
        self.do_test_lmdb_large_key(db)

    def triggle_database_locked(self):
        from xutils.db.driver_sqlite import db_execute

        dbfile = os.path.join(xconfig.DB_DIR, "sqlite", "conflict_test.db")

        if os.path.exists(dbfile):
            os.remove(dbfile)

        con = sqlite3.connect(dbfile)
        # WAL模式，并发度更高，可以允许1写多读，这种模式不会触发数据库锁
        # DELETE模式，写操作是排他的，读操作是共享的
        db_execute(con, "PRAGMA journal_mode = DELETE;")
        db_execute(
            con, "CREATE TABLE IF NOT EXISTS `kv_store` (`key` blob primary key, value blob);")
        con.close()

        class WriteThread(threading.Thread):

            def run(self):
                try:
                    con = sqlite3.connect(dbfile)
                    cur = con.cursor()
                    cur.execute("begin;")
                    cur.execute("DELETE FROM kv_store")
                    cur.execute("COMMIT;")
                    for i in range(100):
                        cur.execute("begin;")
                        cur.execute(
                            "INSERT INTO kv_store (key, value) VALUES (?,?)", ("key_%s" % i, "value"))
                        cur.execute("COMMIT;")
                        print("写入(%d)中..." % i)
                except:
                    xutils.print_exc()
                finally:
                    cur.close()
                    con.commit()
                    con.close()

        class ReadThread(threading.Thread):
            def run(self):
                try:
                    con = sqlite3.connect(dbfile)
                    cur = con.cursor()
                    result = cur.execute("SELECT * FROM kv_store;")
                    for item in result:
                        print("读取执行成功:", item)
                        time.sleep(10)
                        break
                    print("读取结束")
                except:
                    xutils.print_exc()
                finally:
                    cur.close()
                    # con.close()
                    pass

        threads = []

        t = WriteThread()
        t.start()
        threads.append(t)

        for i in range(10):
            t = ReadThread()
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

    def do_test_lmdb_large_key(self, db):
        # type: (dbutil.interfaces.DBInterface) -> None
        # 先清理数据
        for key in db.RangeIter(include_value=False):
            db.Delete(key)
        
        data = list(db.RangeIter())
        self.assertEqual(0, len(data))

        prefix = "test:a_" + textutil.random_string(1000)
        key1 = (prefix + "_key1").encode("utf-8")
        key2 = (prefix + "_key2").encode("utf-8")
        key3 = (prefix + "_key3").encode("utf-8")
        value1 = b"1"
        value2 = b"2"
        value3 = b"3"
        db.Put(key1, value1)
        db.Put(key2, value2)
        db.Put(key3, value3)

        value1b = db.Get(key1)
        self.assertEqual(value1, value1b)

        db.Delete(key1) # 还剩下 key2, key3

        value1c = db.Get(key1)
        self.assertEqual(None, value1c)

        print("-" * 60)
        print("Print Values")

        # 物理视图：一个超长的key
        data = list(db.RangeIterRaw())
        self.assertEqual(1, len(data))

        # 逻辑视图：两个超长的key
        data2 = list(db.RangeIter())
        self.assertEqual(2, len(data2))

        # 插入两个新的超长key
        large_key = "test:b_" + textutil.random_string(1003)
        batch = dbutil.create_write_batch(db_instance=db)
        key4 = large_key + "_key4"
        key5 = large_key + "_key5"

        batch.put(key4, dict(name="test1"))
        batch.put(key5, dict(name="test2"))
        batch.commit()

        # 逻辑视图: 4个超长的key (key2,key3,key4,key5)
        data = list(db.RangeIter())
        keys = []
        for key, value in db.RangeIter():
            keys.append(key)

        print("[RangeIter]", db, data)

        list1 = to_str_list(keys)
        list2 = to_str_list([key2,key3,key4,key5])

        print("list1:", list1)
        print("list2:", list2)

        self.assertEqual(list1, list2)

        # 物理视图: 2个超长key
        self.assertEqual(2, len(list(db.RangeIterRaw())))

    def test_lmdb_large_key2(self):
        from xutils.db.driver_lmdb import LmdbEnhancedKV
        db_dir = os.path.join(xconfig.DB_DIR, "lmdb2")
        # 初始化一个5M的数据库
        db = LmdbEnhancedKV(db_dir, map_size=1024 * 1024 * 5)
        self.do_test_lmdb_large_key(db)

    def test_create_auto_increment_id(self):
        db = dbutil.get_table("test")
        obj1 = Storage(name="Ada", age=20)
        db.insert(obj1, id_type="auto_increment")

        obj2 = Storage(name="Bob", age=21)
        db.insert(obj2, id_type="auto_increment")

        obj3 = Storage(name="Cooper", age=30)
        db.insert(obj3, id_type="auto_increment")

        obj1_found = db.first_by_index("name", index_value="Ada")
        obj2_found = db.first_by_index("name", index_value="Bob")
        obj3_found = db.first_by_index("name", index_value="Cooper")
        obj4_found = db.first_by_index("name", index_value="Other")

        print("obj1_found", obj1_found)
        print("obj2_found", obj2_found)
        print("obj3_found", obj3_found)

        self.assertIsNotNone(obj1_found)
        self.assertIsNotNone(obj2_found)
        self.assertIsNotNone(obj3_found)
        self.assertIsNone(obj4_found)

        assert isinstance(obj1_found, Storage)
        assert isinstance(obj2_found, Storage)
        assert isinstance(obj3_found, Storage)

        self.assertEqual(decode_id(obj1_found._id) +
                         1, decode_id(obj2_found._id))
        self.assertEqual(decode_id(obj2_found._id) +
                         1, decode_id(obj3_found._id))

        results = db.list_by_index("age", limit=10)
        assert isinstance(results, list)

        self.assertEqual(3, len(results))
        self.assertEqual(20, results[0].age)
        self.assertEqual(21, results[1].age)
        self.assertEqual(30, results[2].age)
        self.assertEqual(1, db.count_by_index("name", index_value="Ada"))

        binlog_count = dbutil.count_table("_binlog")
        self.assertTrue(binlog_count > 0)

    def test_db_shard(self):
        from xutils.db.shard import ShardManager

        url1 = "http://localhost:2222/db"
        url2 = "http://localhost:2223/db"
        url3 = "http://localhost:2224/db"

        def Entry(key, value):
            return dict(key=key, value=value)

        class NetMock:

            def http_post(self, url, body=None, charset="utf-8"):
                params = Storage(**json.loads(body))

                if url == url1:
                    resp = self.http_post1(params)
                if url == url2:
                    resp = self.http_post2(params)
                if url == url3:
                    resp = self.http_post3(params)

                return json.dumps(resp)

            def http_post1(self, params):
                if params.offset == 0:
                    return dict(code=0, data=[Entry("a1", "value1"), Entry("b1", "value2")])
                return dict(code=0, data=[])

            def http_post2(self, params):
                if params.offset == 0:
                    return dict(code=0, data=[Entry("a2", "value1"), Entry("b2", "value2")])
                return dict(code=0, data=[])

            def http_post3(self, params):
                if params.offset == 0:
                    return dict(code=0, data=[Entry("a3", "value1"), Entry("b3", "value2")])
                return dict(code=0, data=[])

        netutil.set_net_mock(NetMock())

        shard_manager = ShardManager()
        shard_manager.set_debug(True)
        shard_manager.add_shard(url1)
        shard_manager.add_shard(url2)
        shard_manager.add_shard(url3)

        params = dict(age=20)
        data = shard_manager.query_page(1, 10, params)
        assert isinstance(data, list)

        print("shard page(1,10) query result:", data)

        self.assertEqual(6, len(data))
        self.assertEqual("a1", data[0]["key"])
        self.assertEqual("a2", data[1]["key"])
        self.assertEqual("a3", data[2]["key"])
        self.assertEqual("b1", data[3]["key"])
        self.assertEqual("b2", data[4]["key"])
        self.assertEqual("b3", data[5]["key"])

        data = shard_manager.query_page(2, 3, params)
        assert isinstance(data, list)

        print("shard page(2,3) query result:", data)

        self.assertEqual(3, len(data))
        self.assertEqual("b1", data[0]["key"])
        self.assertEqual("b2", data[1]["key"])
        self.assertEqual("b3", data[2]["key"])

    def test_db_index_page(self):
        self.check_OK("/system/db_index")

        result = json_request("/system/db_index", method="POST",
                              data=dict(action="rebuild", table_name="note_tiny", index_name="name"))

        self.assertEqual("success", result.get("code"))

    def test_dbutil_table_func(self):
        import doctest
        from xutils.db import dbutil_table
        doctest.testmod(m=dbutil_table, verbose=True)

        from xutils.db import encode
        doctest.testmod(m=encode, verbose=True)

    def test_binlog_init(self):
        binlog = BinLog.get_instance()
        binlog.add_log("test", "666")
        binlog.log_debug = False

        with binlog._lock:
            last_seq = binlog.id_gen.current_id_int()
            assert last_seq > 0

            self.assertEqual(binlog._pack_id(last_seq), binlog.get_last_key())
            binlog.add_log("test", "666")

            new_seq = binlog.id_gen.current_id_int()
            self.assertEqual(last_seq+1, new_seq)

    def test_db_index_no_user(self):
        dbutil.register_table("index_test", "索引测试")
        dbutil.register_table_index("index_test", "age")
        dbutil.register_table_index("index_test", "name", index_type="copy")

        obj1 = Storage(name="Ada", age=20)
        db = dbutil.get_table("index_test")
        db.insert(obj1)

        obj2 = Storage(name="Bob", age=21)
        db.insert(obj2)

        result = db.list_by_index("age", index_value=20)
        self.assertEqual(1, len(result))
        self.assertEqual("Ada", result[0].name)

        # 校验索引值是否正确
        obj1_name_index = dbutil.db_get(
            "index_test$name:Ada:" + obj1._id)
        
        assert isinstance(obj1_name_index, Storage)
        self.assertEqual(obj1_name_index.key, "index_test:" + obj1._id)
        self.assertEqual(obj1_name_index.value["name"], "Ada")
        self.assertEqual(obj1_name_index.value["age"], 20)

        obj1["age"] = 25
        db.update(obj1)

        result = db.list_by_index("age", index_value=20)
        self.assertEqual(0, len(result))

        index_count = db.count_by_index("age")
        self.assertEqual(2, index_count)

        db.delete(obj1)

        index_count = db.count_by_index("age")
        self.assertEqual(1, index_count)

    def test_record_lock(self):
        print("test_record_lock")
        from xutils.db.lock import RecordLock

        lock1 = RecordLock("key")
        lock2 = RecordLock("key")

        lock1_result = lock1.acquire(50)
        lock2_result = lock2.acquire(1)

        self.assertTrue(lock1_result)
        self.assertFalse(lock2_result)

        del lock1
        del lock2

    def test_table_only_id(self):
        db = dbutil.get_table("test")

        for item in db.iter(limit = -1):
            db.delete(item)

        db.insert(dict(name="Ada", age=23))
        db.insert(dict(name="Bob", age=22))

        result = db.list(limit=-1)

        print("result:", result)

        self.assertTrue(len(result) > 0)

        first = db.get_first()
        self.assertEqual("Ada", first.name)

        first_id = first._id
        first2 = db.get_by_id(first_id)
        self.assertEqual(first, first2)

        last = db.get_last()
        self.assertEqual("Bob", last.name)

    def test_dbutil_lock(self):
        print("test_dbutil_lock")
        from xutils.db.lock import RecordLock

        RecordLock._lock_dict = dict()

        print(RecordLock._lock_dict)

        self.assertEqual(0, len(RecordLock._lock_dict))

        lock1 = RecordLock("lock")
        lock2 = RecordLock("lock")
        self.assertTrue(lock1.acquire(timeout=10))
        self.assertFalse(lock2.acquire(timeout=0.5))

        lock1.release()
        lock2.release()

        print("_lock_dict", RecordLock._lock_dict)

        self.assertEqual(0, len(RecordLock._lock_dict))

    def test_dbutil_lock_free(self):
        print("test_dbutil_lock_free")
        from xutils.db.lock import RecordLock
        lock1 = RecordLock("lock#1")
        lock2 = RecordLock("lock#2")

        self.assertTrue(lock1.acquire())
        self.assertTrue(lock2.acquire())

        lock1.release()
        lock2.release()

    def test_dbutil_lock_with(self):
        print("test_dbutil_lock_with")
        from xutils.db.lock import RecordLock
        lock1 = RecordLock("lock")
        lock2 = RecordLock("lock")

        with lock1:
            print("test_dbutil_lock_with: lock1 required")
            self.assertFalse(lock2.acquire(timeout=1))
            print("test_dbutil_lock_with: lock2 try acquire failed")

        lock1.release()
        lock2.release()

    def test_binlog_clear(self):
        BinLog.set_max_size(10)

        binlog = BinLog.get_instance()
        # binlog.log_debug = True

        for i in range(20):
            binlog.add_log("put", "test_binlog_clear", "test")
            start_seq = binlog.find_start_seq()
            assert isinstance(start_seq, int)

        binlog.delete_expired()

        self.assertEqual(10, len(binlog.list(0, limit=20)))

    def test_deque_1(self):
        dbutil.register_table("deque_test", "deque测试")

        q = DequeTable("deque_test", max_size=5)
        q.append("v1")
        q.append("v2")
        q.append("v3")
        q.append("v4")

        self.assertEqual(4, len(q))
        batch = dbutil.create_write_batch()
        q.append("v5", batch=batch)
        batch.commit()

        self.assertEqual(5, len(q))

        # 读取队列的数据
        value = q.popleft()
        self.assertEqual(value, "v1")
        self.assertEqual(4, len(q))

        q.append("v6")
        self.assertEqual(q.last(), "v6")
        self.assertEqual(q.first(), "v2")
        self.assertEqual(5, len(q))

    def test_deque_2(self):
        dbutil.register_table("deque_test_2", "deque测试")

        q = DequeTable("deque_test_2", max_size=5)
        q.appendleft("v1")
        q.appendleft("v2")
        q.appendleft("v3")
        q.appendleft("v4")

        self.assertEqual(4, len(q))

        batch = dbutil.create_write_batch()
        q.appendleft("v5", batch=batch)
        batch.commit()

        self.assertEqual(5, len(q))

        # 读取队列的数据
        value = q.pop()
        self.assertEqual(value, "v1")
        self.assertEqual(4, len(q))

        q.appendleft("v6")
        self.assertEqual(q.first(), "v6")
        self.assertEqual(q.last(), "v2")
        self.assertEqual(5, len(q))


    def test_dbutil_sortedset(self):
        db = dbutil.KvSortedSet("sortedset_test")
        self.do_test_sortedset(db)
        db.reset_repair()
        db.repair()

    def do_test_sortedset(self, db):
        assert isinstance(db, interfaces.SortedSetInterface)
        db.put("a", 105)
        db.put("b", 206)

        value = db.get("a")
        self.assertEqual(105, value)

        result = db.list_by_score()
        self.assertEqual(2, len(result))
        self.assertEqual(105, result[0].score)

        db.put("a", 300)
        result = db.list_by_score()
        self.assertEqual(2, len(result))
        self.assertEqual(206, result[0].score)

        by_score = db.list_by_score(score=300)
        assert len(by_score) == 1
        assert by_score[0].member == "a"

        db.delete("b")
        by_score = db.list_by_score(limit=10)
        assert len(by_score) == 1

    def test_dbutil_sortedset_mysql(self):
        print("test_dbutil_sortedset_mysql start...")
        from xutils.db.dbutil_sortedset import RdbSortedSet

        skip_mysql_test = os.environ.get("skip_mysql_test")
        if skip_mysql_test == "True":
            print("skip mysql test")
            return

        db = self.get_mysql_kv()
        xtables.init_kv_zset_table(self.get_mysql_instance())
        RdbSortedSet.init_class(db.db)

        db = RdbSortedSet("sortedset_test")
        self.do_test_sortedset(db)
    
    def test_range_iter_mysql(self):
        from xutils.db.driver_mysql import MySQLKV

        skip_mysql_test = os.environ.get("skip_mysql_test")
        if skip_mysql_test == "True":
            print("skip mysql test")
            return

        engine = self.get_mysql_kv()
        engine.scan_limit = 10

        dbutil.set_driver_name("mysql")
        dbutil.register_table("range_test", "range test")
        db = dbutil.get_table("range_test")

        for i in range(50):
            id = "%03d" % (i+1)
            db.update_by_id(id, dict(name = "test"))
        
        self.assertEqual(50, db.count())
        result = db.list(offset=0,limit=30)
        self.assertEqual(30, len(result))
        self.assertEqual("030", result[-1]._id)


    def test_key_decoder(self):
        from xutils.db.encode import KeyDecoder
        decoder = KeyDecoder("a:b:c")
        a = decoder.pop_left()
        b = decoder.pop_left()
        c = decoder.pop_left()
        d = decoder.pop_left()

        self.assertEqual(a, "a")
        self.assertEqual(b, "b")
        self.assertEqual(c, "c")
        self.assertEqual(d, "")

    def test_key_decoder_rest(self):
        from xutils.db.encode import KeyDecoder
        decoder = KeyDecoder("a:b:c")
        a = decoder.pop_left()
        rest = decoder.rest()
        self.assertEqual(a, "a")
        self.assertEqual(rest, "b:c")

    def test_db_cache(self):
        from xutils.db.dbutil_cache import DatabaseCache
        cache = DatabaseCache()
        cache.delete("test")
        self.assertIsNone(cache.get("test"))
        cache.put("test", 1, expire=100)
        self.assertEqual(cache.get("test"), 1)
        count = cache.clear_expired()
        assert count > 0

    def test_kv_set(self):
        from xutils.db.dbutil_set import KvSetTable
        dbutil.register_table("set_test", "set test")
        table = KvSetTable("set_test")
        table.add("a")
        table.remove("b")
        result = table.list()
        assert set(result) == set(["a"])

        with table.batch() as batch:
            batch.add("x1")
            batch.add("x2")
            batch.add("x3")
            batch.remove("a")
        
        result = table.list()
        print("set result:", result)
        assert set(result) == set(["x1", "x2", "x3"])


    def test_db_admin(self):
        self.check_OK("/system/db/driver_info")
        self.check_OK("/system/db/driver_info?type=sql")
        
        
    def test_index_v2_page(self):
        self.check_OK("/system/db_index?p=meta&p2=index_v2")
