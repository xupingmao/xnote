# -*- coding:utf-8 -*-
"""
MySQL驱动

@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-28 12:29:19
@LastEditors  : xupingmao
@LastEditTime : 2022-09-11 20:23:26
@FilePath     : /xnote/xutils/db/driver_mysql.py
@Description  : mysql驱动
"""

import logging
import threading
import time
import mysql.connector

from xutils.base import Storage
from . import encode


class Holder(threading.local):
    db = None

    def __del__(self):
        if self.db != None:
            self.db.close()


class SqlLoggerInterface:

    def append(self, sql):
        pass


class ConnectionWrapper:

    def __init__(self, db):
        self.db = db  # type: mysql.connector.MySQLConnection

    def __enter__(self):
        return self.db

    def cursor(self, prepared=True):
        return self.db.cursor(prepared=prepared)

    def commit(self):
        return self.db.commit()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()


class MySQLKV:

    holder = Holder()
    lock = threading.RLock()

    def __init__(self, *, host=None, port=3306, user=None, password=None, database=None, pool_size = 0, sql_logger=None):
        self.db_host = host
        self.db_user = user
        self.db_port = port
        self.db_password = password
        self.db_database = database
        self.db_pool_size = pool_size
        self.db_auth_plugin = "mysql_native_password"
        self.max_key_len = 200

        self.debug = True
        self.log_get_profile = True
        self.log_put_profile = True
        self.sql_logger = sql_logger  # type: SqlLoggerInterface

    def get_connection(self):
        # TODO 优化成连接池
        # db = mysql.connector.connect(host=self.db_host, port=self.db_port,
        #                              user=self.db_user, passwd=self.db_password,
        #                              database=self.db_database)
        # if self.holder.db == None:
        # self.holder.db = pymysql.connect(host=self.db_host, port=self.db_port, user=self.db_user, password=self.db_password,
        #                                  database=self.db_database)

        kw = Storage()
        kw.port = self.db_port
        kw.user = self.db_user
        kw.passwd = self.db_password
        kw.database = self.db_database
        if self.db_pool_size > 0:
            kw.pool_size = self.db_pool_size

        con = mysql.connector.connect(host=self.db_host, **kw)
        # return self.holder.db
        return ConnectionWrapper(con)

    def close_cursor(self, cursor):
        pass

    def mysql_to_py(self, obj):
        if isinstance(obj, bytearray):
            return bytes(obj)
        return obj

    def init(self):
        # print("db_host=%s" % self.db_host)
        # print("db_port=%s" % self.db_port)
        # print("db_user=%s" % self.db_user)
        # print("db_password=%s" % self.db_password)
        # print("db_database=%s" % self.db_database)

        with self.get_connection() as con:
            cursor = con.cursor()
            try:
                # tinyblob 最大长度 255
                cursor.execute("""CREATE TABLE IF NOT EXISTS `kv_store` (
                    `key` blob not null comment '键值对key', 
                    value blob comment '键值对value',
                    PRIMARY KEY (`key`(255))
                ) COMMENT '键值对存储';
                """)
                con.commit()
            finally:
                self.close_cursor(cursor)
            logging.info("mysql connection: %s", con)

    def doGet(self, key):
        # type: (bytes) -> bytes
        """通过key读取Value
        @param {bytes} key
        @return {bytes|None} value
        """
        start_time = time.time()
        con = self.get_connection()

        with con:
            cursor = con.cursor(prepared=True)
            try:
                sql = "SELECT value FROM kv_store WHERE `key`=%s"
                cursor.execute(sql, (key, ))
                for result in cursor:
                    return self.mysql_to_py(result[0])
                return None
            finally:
                cost_time = time.time() - start_time
                if self.log_get_profile:
                    logging.debug("GET (%s) cost %.2fms", key, cost_time*1000)

                if self.sql_logger != None:
                    self.sql_logger.append(sql % key)

                self.close_cursor(cursor)

    def Get(self, key):
        if len(key) >= self.max_key_len:
            short_key = key[:self.max_key_len]
            data_bytes = self.doGet(short_key)
            data_dict = encode.convert_bytes_to_dict(data_bytes)
            return data_dict.get(key)
        else:
            return self.doGet(key)

    def doPut(self, cursor, key, value):
        # type: (any,bytes,bytes) -> None
        assert cursor != None
        assert len(key) <= self.max_key_len
        
        select_sql = "SELECT `key` FROM kv_store WHERE `key` = %s"
        insert_sql = "INSERT INTO kv_store (`key`, value) VALUES (%s, %s)"
        update_sql = "UPDATE kv_store SET value=%s WHERE `key` = %s"
        cursor.execute(select_sql, (key, ))
        found = cursor.fetchone()
        if found == None:
            if self.debug:
                logging.debug("SQL:%s, params:%s", insert_sql, (key, value))
            try:
                cursor.execute(insert_sql, (key, value))
            except:
                logging.info("key(%s) exists, try update", key)
                cursor.execute(update_sql, (value, key))
        else:
            if self.debug:
                logging.debug("SQL:%s, params:%s", update_sql, (key, value))

            cursor.execute(update_sql, (value, key))

    def doPutLong(self, cursor, key, value):
        if len(key) >= self.max_key_len:
            short_key = key[:self.max_key_len]
            with self.lock:
                data_bytes = self.doGet(short_key)
                data_dict = encode.convert_bytes_to_dict(data_bytes)
                data_dict[key] = value
                self.doPut(cursor, short_key, encode.convert_bytes_dict_to_bytes(data_dict))
        else:
            return self.doPut(cursor, key, value)

    def Put(self, key, value, sync=False, cursor=None):
        # type: (bytes,bytes,bool,any) -> None
        """写入Key-Value键值对
        @param {bytes} key
        @param {bytes} value
        """

        start_time = time.time()

        if cursor != None:
            return self.doPutLong(cursor, key, value)

        con = self.get_connection()
        with con:
            cursor = con.cursor(prepared=True)
            try:
                self.doPutLong(cursor, key, value)
                con.commit()
            finally:
                cost_time = time.time() - start_time
                if self.log_put_profile:
                    logging.debug("Put (%s) cost %.2fms", key, cost_time*1000)
                self.close_cursor(cursor)

    def doDeleteRaw(self, key, sync=False, cursor=None):
        # type: (bytes, bool, any) -> None
        """删除Key-Value键值对
        @param {bytes} key
        """
        assert len(key) <= self.max_key_len

        sql = "DELETE FROM kv_store WHERE `key` = %s;"
        if self.debug:
            logging.debug("SQL:%s, params:%s", sql, (key, ))

        cursor.execute(sql, (key, ))
    
    def doDeleteLongNoLock(self, key, cursor):
        short_key = key[:self.max_key_len]
        data_bytes = self.doGet(short_key)
        data_dict = encode.convert_bytes_to_dict(data_bytes)
        if key in data_dict:
            del data_dict[key]
            
        if len(data_dict) == 0:
            self.doDeleteRaw(short_key, cursor = cursor)
        else:
            self.doPut(cursor, short_key, encode.convert_bytes_dict_to_bytes(data_dict))

    def doDelete(self, key, sync=False, cursor=None):
        assert cursor != None

        if len(key) >= self.max_key_len:
            with self.lock:
                self.doDeleteLongNoLock(key, cursor)
        else:
            return self.doDeleteRaw(key, sync, cursor)

    def Delete(self, key, sync=False):
        con = self.get_connection()
        with con:
            cursor = con.cursor(prepared=True)
            try:
                self.doDelete(key, cursor=cursor)
            finally:
                self.close_cursor(cursor)    
    
    def RangeIterRaw(self,
                  key_from=None,
                  key_to=None,
                  *,
                  reverse=False,
                  include_value=True,
                  fill_cache=False):
        """返回区间迭代器
        @param {bytes}  key_from       开始的key（包含）FirstKey
        @param {bytes}  key_to         结束的key（包含）LastKey
        @param {bool}   reverse        是否反向查询
        @param {bool}   include_value  是否包含值
        @param {bool}   fill_cache     是否填充缓存
        """

        # 优化成轮询的短查询
        con = self.get_connection()
        limit = 100

        with con:
            cursor = con.cursor(prepared=True)
            try:
                sql_builder = []

                if include_value:
                    sql_builder.append("SELECT `key`, value FROM kv_store")
                else:
                    # 只包含key
                    sql_builder.append("SELECT `key` FROM kv_store")

                if key_from != None or key_to != None:
                    sql_builder.append("WHERE 1=1")

                if key_from != None:
                    sql_builder.append("AND `key` >= %s")

                if key_to != None:
                    sql_builder.append("AND `key` <= %s")

                if reverse:
                    sql_builder.append("ORDER BY `key` DESC")

                sql_builder.append("LIMIT %d;" % (limit + 1))

                sql = " ".join(sql_builder)

                has_next = True
                while has_next:
                    params = []
                    if key_from != None:
                        params.append(key_from)

                    if key_to != None:
                        params.append(key_to)

                    if self.debug:
                        logging.debug("SQL:%s (%s)", sql, params)

                    cursor.execute(sql, tuple(params))
                    if self.sql_logger:
                        self.sql_logger.append(sql % tuple(params))

                    # return cur.execute(sql, tuple(params))
                    result = cursor.fetchall()

                    for item in result[:limit]:
                        # logging.debug("include_value(%s), item:%s", include_value, item)
                        key = self.mysql_to_py(item[0])

                        if include_value:
                            if item[1] == None:
                                continue
                            yield key, self.mysql_to_py(item[1])
                        else:
                            yield key

                    if len(result) <= limit:
                        break

                    last_key = self.mysql_to_py(result[-1][0])
                    if reverse:
                        key_to = last_key
                    else:
                        key_from = last_key

            finally:
                self.close_cursor(cursor)

    def RangeIter(self, *args, **kw):
        include_value = kw.get("include_value", True)
        reverse = kw.get("reverse", False)

        if include_value:
            for key, value_bytes in self.RangeIterRaw(*args, **kw):
                if len(key) >= self.max_key_len:
                    value_dict = encode.convert_bytes_to_dict(value_bytes)
                    for key in sorted(value_dict.keys(), reverse=reverse):
                        value = value_dict[key]
                        yield key, value
                else:
                    yield key, value_bytes
        else:
            for key in self.RangeIterRaw(*args, **kw):
                if len(key) >= self.max_key_len:
                    value_bytes = self.doGet(key)
                    value_dict = encode.convert_bytes_to_dict(value_bytes)
                    # 必须要保证key的迭代顺序
                    for fullkey in sorted(value_dict.keys(), reverse=reverse):
                        yield fullkey
                else:
                    yield key

    def CreateSnapshot(self):
        raise NotImplementedError("CreateSnapshot")

    def Write(self, batch, sync=False):
        con = self.get_connection()
        with con:
            cursor = con.cursor(prepared=False)
            try:
                cursor.execute("begin;")
                for key in batch._puts:
                    value = batch._puts[key]
                    self.Put(key, value, cursor=cursor)

                for key in batch._deletes:
                    self.doDelete(key, cursor=cursor)
                cursor.execute("commit;")
            finally:
                self.close_cursor(cursor)
