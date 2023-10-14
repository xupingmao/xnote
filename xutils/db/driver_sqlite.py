# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/10/24 11:11:04
# @modified 2022/04/17 14:15:34
# @filename driver_sqlite.py

"""Sqlite对KV接口的实现"""

import sqlite3
import threading
import logging
import web.db
import time

from xutils.mem_util import log_mem_info_deco
from xutils import interfaces

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

class SqliteKV(interfaces.DBInterface):

    _lock = interfaces.get_write_lock()
    
    sql_logger = interfaces.SqlLoggerInterface()

    def __init__(self, db_file, snapshot=None,
                 block_cache_size=None,
                 write_buffer_size=None,
                 config_dict={},
                 debug=True):
        """通过 sqlite 来实现leveldb的接口代理"""
        self.db_file = db_file
        self.db = web.db.SqliteDB(db = db_file)
        self.debug = debug
        self.config_dict = config_dict
        self.is_snapshot = False
        self.init_journal_mode()

        if snapshot != None:
            # sqlite并不支持快照，这里模拟下
            self.is_snapshot = True

    def init_journal_mode(self):
        # db_holder是threadlocal对象，这里是线程安全的
        logging.info("init_journal_mode")
        config_dict = self.config_dict

        with self._lock:
            # 设置 isolation_level=None 开启自动提交
            # db = sqlite3.connect(self.db_file, isolation_level=None)
            journal_mode = config_dict.get("sqlite_journal_mode", "").lower()
            if config_dict != None and journal_mode == "wal":
                # WAL模式，并发度更高
                self.db.query("PRAGMA journal_mode = WAL;")
            else:
                self.db.query("PRAGMA journal_mode = DELETE;")

            # db_execute(self.db_holder.db, "PRAGMA journal_mode = DELETE;") # 默认模式
            self.db.query("CREATE TABLE IF NOT EXISTS `kv_store` (`key` blob primary key, value blob);")

    def _commit(self):
        """PEP 249要求 Python 数据库驱动程序默认以手动提交模式运行"""
        pass

    def log_sql(self, sql="", vars=None, prefix=""):
        if self.sql_logger:
            raw_sql = self.db.query(sql, vars=vars, _test=True)
            self.sql_logger.append(f"{prefix} {raw_sql}")

    @log_mem_info_deco("db.Get")
    def Get(self, key):
        sql = "SELECT value FROM kv_store WHERE `key` = $key;"
        vars = dict(key=key)
        r_iter = self.db.query(sql, vars=vars)
        result = list(r_iter)
        self.log_sql(sql, vars=vars, prefix="[Get]")
        if len(result) > 0:
            return result[0].value
        return None


    def BatchGet(self, key_list):
        # type: (list[bytes]) -> dict[bytes, bytes]
        if len(key_list) == 0:
            return {}

        start_time = time.time()

        sql = ""
        vars = dict(key_list=key_list)
        try:
            result = dict()
            sql = "SELECT `key`, value FROM kv_store WHERE `key` IN $key_list"
            result_iter = self.db.query(sql, vars=vars)
            for item in result_iter:
                key = item.key
                value = item.value
                result[key] = value
            return result
        finally:
            cost_time = time.time() - start_time
            if self.debug:
                raw_sql = self.db.query(sql, vars=vars, _test=True)
                self.sql_logger.append(f"[BatchGet {cost_time:.2f}ms] {raw_sql}")
    
    def _exists(self, key, cursor=None):
        sql = "SELECT `key` FROM kv_store WHERE `key` = $key;"
        vars = dict(key=key)
        result = list(self.db.query(sql, vars=vars))
        if self.debug:
            raw_sql = self.db.query(sql, vars=vars, _test=True)
            self.sql_logger.append(f"[_exists] {raw_sql}")

        return len(result) > 0

    def Put(self, key, value, sync=False):
        return self.doPut(key, value, sync)

    def doPut(self, key, value, sync=False, cursor=None):
        if self.debug:
            logging.debug("Put: key(%s), value(%s)", key, value)

        if value is None:
            return self.doDelete(key, cursor=cursor)

        with self._lock:
            try:
                # 不使用 REPLACE INTO, 因为 REPLACE INTO 会直接删除数据重新插入, rowid会一直增加
                # UPSERT语法比较晚支持，暂时不用
                if self._exists(key, cursor=cursor):
                    sql = "UPDATE kv_store SET value = $value WHERE `key` = $key;"
                else:
                    sql = "INSERT INTO kv_store (`key`, value) VALUES ($key, $value);"
                vars = dict(key=key, value=value)
                self.db.query(sql, vars=vars)
                self.log_sql(sql, vars=vars, prefix="[Put]")
            except Exception as e:
                raise e

    def Insert(self, key=b'', value=b''):
        insert_sql = "INSERT INTO kv_store (`key`, value) VALUES ($key, $value)"
        vars = dict(key=key,value=value)
        self.db.query(insert_sql, vars=vars)

    def Delete(self, key, sync=False):
        return self.doDelete(key, sync)

    def doDelete(self, key, sync=False, cursor=None):
        sql = "DELETE FROM kv_store WHERE key = $key;"
        vars = dict(key=key)
        
        if self.debug:
            raw_sql = self.db.query(sql, vars=vars, _test=True)
            self.sql_logger.append(f"Delete: {raw_sql}")

        with self._lock:
            return self.db.query(sql, vars=vars)

    def RangeIter(self, *args, **kw):
        yield from self.RangeIterNoLock(*args, **kw)

    def RangeIterNoLock(self, key_from=None, key_to=None,
                        reverse=False, include_value=True, fill_cache=False):
        has_next = True
        limit = 100

        sql_builder = []

        if include_value:
            sql_builder.append("SELECT `key`, value FROM kv_store")
        else:
            # 只包含key
            sql_builder.append("SELECT `key` FROM kv_store")

        sql_builder.append("WHERE `key` >= $key_from AND `key` <= $key_to")

        if reverse:
            sql_builder.append("ORDER BY key DESC")
        else:
            sql_builder.append("ORDER BY key ASC")

        sql_builder.append("LIMIT %s" % (limit+1))
        sql_builder.append(";")

        sql = " ".join(sql_builder)

        while has_next:
            if key_from == None:
                key_from = b''

            if key_to == None:
                key_to = b'\xff'

            vars = dict(key_from=key_from, key_to=key_to)
            result_iter = self.db.query(sql, vars=vars)
            result = list(result_iter)

            if self.debug:
                raw_sql = self.db.query(sql, vars=vars, _test=True)
                self.sql_logger.append(f"[RangeIterNoLock rows:{len(result)}] {raw_sql}")
            
            # return cur.execute(sql, tuple(params))
            for item in result[:limit]:
                if include_value:
                    if item.value == None:
                        continue
                    yield item.key, item.value
                else:
                    yield item.key

            has_next = len(result) > limit

            if len(result) == 0:
                return

            last_key = result[-1].key
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
        sql_builder = []

        if include_value:
            sql_builder.append("SELECT `key`, value FROM kv_store")
        else:
            # 只包含key
            sql_builder.append("SELECT `key` FROM kv_store")

        vars = dict()

        if key_from != None or key_to != None:
            sql_builder.append("WHERE 1=1")

        if key_from != None:
            sql_builder.append("AND `key` >= $key_from")
            vars["key_from"] = key_from

        if key_to != None:
            sql_builder.append("AND `key` <= $key_to")
            vars["key_to"] = key_to

        if reverse:
            sql_builder.append("ORDER BY key DESC")

        sql_builder.append(";")

        sql = " ".join(sql_builder)

        if self.debug:
            raw_sql = self.db.query(sql, vars=vars, _test=True)
            self.sql_logger.append(f"[RangeIterWithLock] {raw_sql}")

        # return cur.execute(sql, tuple(params))
        for item in self.db.query(sql, vars=vars):
            # logging.debug("include_value(%s), item:%s", include_value, item)
            if include_value:
                if item.value == None:
                    continue
                yield item.key, item.value
            else:
                yield item.key

    def CreateSnapshot(self):
        return self

    @log_mem_info_deco("db.Write")
    def Write(self, batch, sync=False):
        """执行批量操作"""
        assert isinstance(batch, interfaces.BatchInterface)
        # return self._db.write(batch, sync)
        if len(batch._puts) + len(batch._deletes) + len(batch._inserts) == 0:
            return
        

        with self._lock:
            with self.db.transaction():
                for key in batch._puts:
                    value = batch._puts[key]
                    self.doPut(key, value)
                
                for key in batch._inserts:
                    value = batch._inserts[key]
                    self.Insert(key, value)

                for key in batch._deletes:
                    self.doDelete(key)


    def Count(self, key_from=b'', key_to=b'\xff'):
        sql = "SELECT COUNT(*) AS amount FROM kv_store WHERE `key` >= $key_from AND `key` <= $key_to"
        start_time = time.time()
        vars = dict(key_from=key_from, key_to=key_to)
        try:
            result_iter = self.db.query(sql, vars=vars)
            for row in result_iter:
                return row.amount
            return 0
        finally:
            if self.debug:
                cost_time = time.time() - start_time
                sql_query = self.db.query(sql, vars=vars, _test=True)
                self.sql_logger.append(f"[Count {cost_time*100:.2f}ms] {sql_query}")
                
    def Close(self):
        self.db.ctx.db.close()
        del self.db

