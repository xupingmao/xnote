# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/10/24 11:11:04
# @modified 2022/04/17 14:15:34
# @filename driver_sqlite.py

"""Sqlite对KV接口的实现"""

import sqlite3
import threading
import logging
from xutils.mem_util import log_mem_info_deco
from . import driver_interface

class FreeLock:

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        # print("__exit__", type, value, traceback)
        pass


def db_execute(db, sql, *args):
    cursorobj = db.cursor()
    try:
        cursorobj.execute(sql, args)
        kv_result = []
        result = cursorobj.fetchall()
        for single in result:
            resultMap = {}
            for i, desc in enumerate(cursorobj.description):
                name = desc[0]
                resultMap[name] = single[i]
            kv_result.append(resultMap)
        db.commit()
        return kv_result
    except Exception:
        db.rollback()
        raise
    finally:
        cursorobj.close()


class Holder(threading.local):
    def __init__(self):
        self.db: sqlite3.Connection = None

    def __del__(self):
        if self.db != None:
            self.db.close()

class SqliteKV(driver_interface.DBInterface):

    _lock = threading.RLock()

    def __init__(self, db_file, snapshot=None,
                 block_cache_size=None,
                 write_buffer_size=None,
                 config_dict=None,
                 debug=True):
        """通过 sqlite 来实现leveldb的接口代理"""
        self.db_file = db_file
        self.debug = debug
        self.config_dict = config_dict
        self.is_snapshot = False

        if snapshot != None:
            # sqlite并不支持快照，这里模拟下
            self._db = snapshot
            self.is_snapshot = True
        else:
            self._db = None
        
        self.db_holder = Holder()

    def init_db_connection(self):
        # db_holder是threadlocal对象，这里是线程安全的
        logging.info("init_db_connection")
        config_dict = self.config_dict

        with self._lock:
            # 设置 isolation_level=None 开启自动提交
            db = sqlite3.connect(self.db_file, isolation_level=None)

            if config_dict != None and config_dict.sqlite_journal_mode == "WAL":
                db_execute(db, "PRAGMA journal_mode = WAL;")
            else:
                # WAL模式，并发度更高
                db_execute(db, "PRAGMA journal_mode = DELETE;")

            # db_execute(self.db_holder.db, "PRAGMA journal_mode = DELETE;") # 默认模式
            db_execute(db, "CREATE TABLE IF NOT EXISTS `kv_store` (`key` blob primary key, value blob);")

        return db

    def _get_db(self):
        if self._db != None:
            return self._db
        
        if self.db_holder.db == None:
            # 这是一个 threadlocal
            self.db_holder.db = self.init_db_connection()
            
        return self.db_holder.db

    def cursor(self):
        db = self._get_db()
        return db.cursor()

    def commit(self):
        """PEP 249要求 Python 数据库驱动程序默认以手动提交模式运行"""
        if self._db != None:
            self._db.commit()
        else:
            self.db_holder.db.commit()

    def rollback(self):
        if self._db != None:
            self._db.rollback()
        else:
            self.db_holder.db.rollback()

    @log_mem_info_deco("db.Get")
    def Get(self, key):
        cursor = self.cursor()
        try:
            sql = "SELECT value FROM kv_store WHERE `key` = ?;"
            r_iter = cursor.execute(sql, (key,))
            result = list(r_iter)
            if self.debug:
                logging.info("SQL:%s, key:%s, rows:%s", sql, key, len(result))
            if len(result) > 0:
                return result[0][0]
            return None
        finally:
            cursor.close()

    def _exists(self, key, cursor=None):
        assert cursor != None
        sql = "SELECT `key` FROM kv_store WHERE `key` = ?;"
        cursor.execute(sql, (key,))
        result = cursor.fetchall()
        if self.debug:
            logging.info("SQL:%s, key:%s, rows:%s", sql, key, len(result))

        return len(result) > 0

    def Put(self, key, value, sync=False):
        cursor = self.cursor()
        try:
            return self.doPut(key, value, sync, cursor=cursor)
        finally:
            cursor.close()

    def doPut(self, key, value, sync=False, cursor=None):
        assert cursor != None
        if self.debug:
            logging.debug("Put: key(%s), value(%s)", key, value)

        if value is None:
            return self.doDelete(key, cursor=cursor)

        with self._lock:
            try:
                if self._exists(key, cursor=cursor):
                    cursor.execute(
                        "UPDATE kv_store SET value = ? WHERE `key` = ?;", (value, key))
                else:
                    cursor.execute(
                        "INSERT INTO kv_store (`key`, value) VALUES (?,?);", (key, value))

            except Exception as e:
                raise e

    def Delete(self, key, sync=False):
        cursor = self.cursor()
        try:
            return self.doDelete(key, sync, cursor=cursor)
        finally:
            cursor.close()

    def doDelete(self, key, sync=False, cursor=None):
        assert cursor != None
        if self.debug:
            logging.debug("Delete: key(%s)", key)

        with self._lock:
            try:
                cursor.execute("DELETE FROM kv_store WHERE key = ?;", (key,))
            except Exception as e:
                raise e

    def RangeIter(self, *args, **kw):
        yield from self.RangeIterNoLock(*args, **kw)

    def RangeIterNoLock(self, key_from=None, key_to=None,
                        reverse=False, include_value=True, fill_cache=False):
        has_next = True
        limit = 100

        sql_builder = []

        if include_value:
            sql_builder.append("SELECT key, value FROM kv_store")
        else:
            # 只包含key
            sql_builder.append("SELECT key FROM kv_store")

        sql_builder.append("WHERE key >= ? AND key <= ?")

        if reverse:
            sql_builder.append("ORDER BY key DESC")
        else:
            sql_builder.append("ORDER BY key ASC")

        sql_builder.append("LIMIT %s" % (limit+1))
        sql_builder.append(";")

        sql = " ".join(sql_builder)

        while has_next:
            params = []
            if key_from != None:
                params.append(key_from)
            else:
                params.append(b"")

            if key_to != None:
                params.append(key_to)
            else:
                params.append(b"\xff")

            cur = self.cursor()
            try:
                cur.execute(sql, tuple(params))
                result = cur.fetchall()
            finally:
                cur.close()

            if self.debug:
                logging.debug("SQL:%s (%s) rows:%s", sql, params, len(result))
            
            # return cur.execute(sql, tuple(params))
            for item in result[:limit]:
                if include_value:
                    if item[1] == None:
                        continue
                    yield item
                else:
                    yield item[0]

            has_next = len(result) > limit

            if len(result) == 0:
                return

            last_key = result[-1][0]
            if reverse:
                key_to = last_key
            else:
                key_from = last_key

    def RangeIterWithLock(self, key_from=None, key_to=None,
                          reverse=False, include_value=True,
                          fill_cache=False):
        """返回区间迭代器
        @param {str}  key_from       开始的key（包含） FirstKey  MinKey
        @param {str}  key_to         结束的key（包含） LastKey   MaxKey
        @param {bool} reverse        是否反向查询
        @param {bool} include_value  是否包含值
        """
        cur = self.cursor()
        sql_builder = []
        params = []

        if include_value:
            sql_builder.append("SELECT key, value FROM kv_store")
        else:
            # 只包含key
            sql_builder.append("SELECT key FROM kv_store")

        if key_from != None or key_to != None:
            sql_builder.append("WHERE 1=1")

        if key_from != None:
            sql_builder.append("AND key >= ?")
            params.append(key_from)

        if key_to != None:
            sql_builder.append("AND key <= ?")
            params.append(key_to)

        if reverse:
            sql_builder.append("ORDER BY key DESC")

        sql_builder.append(";")

        sql = " ".join(sql_builder)

        if self.debug:
            logging.debug("SQL:%s (%s)", sql, params)

        try:
            # return cur.execute(sql, tuple(params))
            for item in cur.execute(sql, tuple(params)):
                # logging.debug("include_value(%s), item:%s", include_value, item)
                if include_value:
                    if item[1] == None:
                        continue
                    yield item
                else:
                    yield item[0]
        finally:
            cur.close()

    def CreateSnapshot(self):
        return self

    @log_mem_info_deco("db.Write")
    def Write(self, batch, sync=False):
        """执行批量操作"""
        # return self._db.write(batch, sync)
        if len(batch._puts) + len(batch._deletes) == 0:
            return

        with self._lock:
            cur = self.cursor()
            try:
                cur.execute("begin;")
                for key in batch._puts:
                    value = batch._puts[key]
                    self.doPut(key, value, cursor=cur)

                for key in batch._deletes:
                    self.doDelete(key, cursor=cur)

                cur.execute("commit;")
                self.commit()
            except Exception as e:
                cur.execute("rollback;")
                raise e
            finally:
                cur.close()

    def Close(self):
        if self._db != None:
            self._db.close()
        else:
            self.db_holder.db.close()
