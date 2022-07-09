# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/10/24 11:11:04
# @modified 2022/04/17 14:15:34
# @filename driver_sqlite.py

"""Sqlite对KV接口的实现"""

import sqlite3
import threading
import logging


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
    db = None

    def __del__(self):
        if self.db != None:
            self.db.close()

class CursorWrapper:

    def __init__(self, db, cursor = None):
        if cursor is None:
            self.cursor = db.cursor()
            self.is_new = True
        else:
            self.cursor = cursor
            self.is_new = False

    def close(self):
        if self.is_new:
            self.cursor.close()

    def commit(self):
        if self.is_new:
            self.cursor.commit()

    def rollback(self):
        if self.is_new:
            self.cursor.rollback()


def close_cursor(cursor, is_new_cursor):
    if is_new_cursor:
        cursor.close()

class SqliteKV:

    _lock = threading.RLock()

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

    def _get_db(self):
        if self._db != None:
            return self._db

        if self.db_holder.db == None:
            # db_holder是threadlocal对象，这里是线程安全的
            logging.info("init db")
            with self._lock:
                self.db_holder.db = sqlite3.connect(self.db_file)
                db_execute(self.db_holder.db, "PRAGMA journal_mode = WAL;") # WAL模式，并发度更高
                # db_execute(self.db_holder.db, "PRAGMA journal_mode = DELETE;") # 默认模式
                db_execute(self.db_holder.db, "CREATE TABLE IF NOT EXISTS `kv_store` (`key` blob primary key, value blob);")

        return self.db_holder.db

    def cursor(self):
        db = self._get_db()
        return db.cursor()

    def commit(self):
        if self._db != None:
            self._db.commit()
        else:
            self.db_holder.db.commit()

    def check_and_commit(self, is_new_cursor):
        if is_new_cursor:
            self.commit()

    def rollback(self):
        if self._db != None:
            self._db.rollback()
        else:
            self.db_holder.db.rollback()

    def check_and_rollback(self, is_new):
        if is_new:
            self.rollback()

    def Get(self, key):
        cursor = self.cursor()
        try:
            r_iter = cursor.execute("SELECT value FROM kv_store WHERE `key` = ?;", (key,))
            result = list(r_iter)
            if len(result) > 0:
                return result[0][0]
            return None
        finally:
            cursor.close()

    def _exists(self, key):
        cursor = self.cursor()
        r_iter = cursor.execute("SELECT `key` FROM kv_store WHERE `key` = ?;", (key,))
        result = list(r_iter)
        return len(result) > 0

    def Put(self, key, value, sync = False, cursor = None):
        if self.debug:
            logging.debug("Put: key(%s), value(%s)", key, value)

        if value is None:
            return self.Delete(key, cursor = cursor)

        is_new = False
        if cursor == None:
            is_new = True
            cursor = self.cursor()

        with self._lock:
            try:
                if self._exists(key):
                    cursor.execute("UPDATE kv_store SET value = ? WHERE `key` = ?;", (value, key))
                else:
                    cursor.execute("INSERT INTO kv_store (`key`, value) VALUES (?,?);", (key, value))

                self.check_and_commit(is_new)
            except Exception as e:
                self.check_and_rollback(is_new)
                raise e
            finally:
                close_cursor(cursor, is_new)

    def Delete(self, key, sync = False, cursor = None):
        if self.debug:
            logging.debug("Delete: key(%s)", key)
        
        is_new = False
        if cursor == None:
            cursor = self.cursor()
            is_new = True

        with self._lock:
            try:
                cursor.execute("DELETE FROM kv_store WHERE key = ?;", (key,))
                self.check_and_commit(is_new)
            except Exception as e:
                self.check_and_rollback(is_new)
                raise e
            finally:
                close_cursor(cursor, is_new)


    def RangeIter(self, key_from = None, key_to = None, 
            reverse = False, include_value = True, 
            fill_cache = False):
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

    def Write(self, batch, sync = False):
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
                    self.Put(key, value, cursor = cur)

                for key in batch._deletes:
                    self.Delete(key, cursor = cur)
                cur.execute("commit;")
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


