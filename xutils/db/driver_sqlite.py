# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/10/24 11:11:04
# @modified 2022/04/06 12:46:25
# @filename driver_sqlite.py

"""Sqlite对KV接口的实现"""

import sqlite3
import threading
import logging


_write_lock = threading.RLock()

def get_write_lock():
    return _write_lock

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
        return kv_result
    except Exception:
        raise
    finally:
        db.commit()

class Holder(threading.local):
    db = None

    def __del__(self):
        if self.db != None:
            self.db.close()

class SqliteKV:

    def __init__(self, db_file, snapshot = None, 
            block_cache_size = None, 
            write_buffer_size = None,
            debug = True):
        """通过leveldbpy来实现leveldb的接口代理，因为leveldb没有提供Windows环境的支持"""
        self.db_file = db_file
        self.db_holder = Holder()
        self.debug = debug

        if snapshot != None:
            self._db = snapshot
        else:
            self._db = None

    def cursor(self):
        if self._db != None:
            return self._db.cursor()

        if self.db_holder.db == None:
            # db_holder是threadlocal对象，这里是线程安全的
            logging.info("init db")
            with get_write_lock():
                self.db_holder.db = sqlite3.connect(self.db_file)
                db_execute(self.db_holder.db, "PRAGMA journal_mode = WAL;") # WAL模式，并发度更高
                # db_execute(self.db_holder.db, "PRAGMA journal_mode = DELETE;") # 默认模式
                db_execute(self.db_holder.db, "CREATE TABLE IF NOT EXISTS `kv_store` (`key` blob primary key, value blob);")

        return self.db_holder.db.cursor()

    def commit(self):
        if self._db != None:
            self._db.commit()
        else:
            self.db_holder.db.commit()

    def Get(self, key):
        cursor = self.cursor()
        r_iter = cursor.execute("SELECT value FROM kv_store WHERE `key` = ?;", (key,))
        result = list(r_iter)
        if len(result) > 0:
            return result[0][0]
        return None

    def _exists(self, key):
        cursor = self.cursor()
        r_iter = cursor.execute("SELECT `key` FROM kv_store WHERE `key` = ?;", (key,))
        result = list(r_iter)
        return len(result) > 0

    def Put(self, key, value, sync = False, cursor = None):
        arg_cursor = cursor

        if self.debug:
            logging.debug("Put: key(%s), value(%s)", key, value)

        if value is None:
            return self.Delete(key, cursor = cursor)

        with get_write_lock():
            if cursor == None:
                cursor = self.cursor()
            try:
                if self._exists(key):
                    cursor.execute("UPDATE kv_store SET value = ? WHERE `key` = ?;", (value, key))
                else:
                    cursor.execute("INSERT INTO kv_store (`key`, value) VALUES (?,?);", (key, value))
            finally:
                if arg_cursor is None:
                    self.commit()

    def Delete(self, key, sync = False, cursor = None):
        arg_cursor = cursor
        if self.debug:
            logging.debug("Delete: key(%s)", key)
        
        with get_write_lock():
            if cursor == None:
                cursor = self.cursor()

            try:
                cursor.execute("DELETE FROM kv_store WHERE key = ?;", (key,))
            finally:
                if arg_cursor is None:
                    self.commit()


    def RangeIter(self, key_from = None, key_to = None, 
            reverse = False, include_value = True, 
            fill_cache = False):
        """返回区间迭代器
        @param {str}  key_from       开始的key（包含） FirstKey
        @param {str}  key_to         结束的key（包含） LastKey
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

        # return cur.execute(sql, tuple(params))
        for item in cur.execute(sql, tuple(params)):
            # logging.debug("include_value(%s), item:%s", include_value, item)
            if include_value:
                if item[1] == None:
                    continue
                yield item
            else:
                yield item[0]


    def CreateSnapshot(self):
        return self

    def Write(self, batch, sync = False):
        """执行批量操作"""
        # return self._db.write(batch, sync)
        if len(batch._puts) + len(batch._deletes) == 0:
            return

        with get_write_lock():
            cur = self.cursor()
            try:
                cur.execute("begin;")
                for key in batch._puts:
                    value = batch._puts[key]
                    self.Put(key, value, cursor = cur)

                for key in batch._deletes:
                    self.Delete(key, cursor = cur)
            finally:
                self.commit()

    def Close(self):
        if self._db != None:
            self._db.close()
        else:
            self.db_holder.db.close()


