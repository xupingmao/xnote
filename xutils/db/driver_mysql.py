# -*- coding:utf-8 -*-
"""
开发中...

@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-28 12:29:19
@LastEditors  : xupingmao
@LastEditTime : 2022-09-04 16:40:01
@FilePath     : /xnote/xutils/db/driver_mysql.py
@Description  : mysql驱动
"""

import logging
import threading
import time
import mysql.connector


class Holder(threading.local):
    db = None

    def __del__(self):
        if self.db != None:
            self.db.close()


class ConnectionWrapper:

    def __init__(self, db):
        self.db = db # type: mysql.connector.MySQLConnection
    
    def __enter__(self):
        return self.db
    
    def cursor(self, prepared = True):
        return self.db.cursor(prepared = prepared)
    
    def commit(self):
        return self.db.commit()

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class MySQLKv:

    holder = Holder()

    def __init__(self, *, host=None, port=3306, user=None, password=None, database=None):
        self.db_host = host
        self.db_user = user
        self.db_port = port
        self.db_password = password
        self.db_database = database
        self.debug = True
        self.log_get_profile = True
        self.log_put_profile = True

    def get_connection(self):
        # TODO 优化成连接池
        db = mysql.connector.connect(host=self.db_host, port=self.db_port,
                                     user=self.db_user, passwd=self.db_password,
                                     database=self.db_database)
        # if self.holder.db == None:
        #     self.holder.db = pymysql.connect(host=self.db_host, port=self.db_port, user=self.db_user, password=self.db_password,
        #                                      database=self.db_database)
        # return self.holder.db

        return ConnectionWrapper(db)
    
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

    def Get(self, key):
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
                self.close_cursor(cursor)

    def doPut(self, cursor, key, value):
        # type: (any,bytes,bytes) -> None
        select_sql = "SELECT value FROM kv_store WHERE `key` = %s FOR UPDATE"
        insert_sql = "INSERT INTO kv_store (`key`, value) VALUES (%s, %s)"
        update_sql = "UPDATE kv_store SET value=%s WHERE `key` = %s"
        cursor.execute(select_sql, (key, ))
        found = cursor.fetchone()
        if found == None:
            if self.debug:
                logging.debug("SQL:%s, params:%s", insert_sql, (key, value))

            cursor.execute(insert_sql, (key, value))
        else:
            if self.debug:
                logging.debug("SQL:%s, params:%s", update_sql, (key, value))

            cursor.execute(update_sql, (value, key))

    def Put(self, key, value, sync=False, cursor=None):
        # type: (bytes,bytes,bool,any) -> None
        """写入Key-Value键值对
        @param {bytes} key
        @param {bytes} value
        """
        start_time = time.time()

        if cursor != None:
            return self.doPut(cursor, key, value)

        con = self.get_connection()
        with con:
            cursor = con.cursor(prepared=True)
            try:
                self.doPut(cursor, key, value)
                con.commit()
            finally:
                cost_time = time.time() - start_time
                if self.log_put_profile:
                    logging.debug("Put (%s) cost %.2fms", key, cost_time*1000)
                self.close_cursor(cursor)

    def Delete(self, key, sync=False, cursor=None):
        # type: (bytes, bool, any) -> None
        """删除Key-Value键值对
        @param {bytes} key
        """
        sql = "DELETE FROM kv_store WHERE `key` = %s;"
        if self.debug:
            logging.debug("SQL:%s, params:%s", sql, (key, ))

        if cursor != None:
            cursor.execute(sql, (key, ))
            return

        con = self.get_connection()
        with con:
            cursor = con.cursor(prepared=True)
            try:
                cursor.execute(sql, (key, ))
                con.commit()
            finally:
                self.close_cursor(cursor)

    def RangeIter(self,
                  key_from=None,
                  key_to=None,
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
        con = self.get_connection()
        with con:
            cursor = con.cursor(prepared=True)
            try:
                sql_builder = []
                params = []

                if include_value:
                    sql_builder.append("SELECT `key`, value FROM kv_store")
                else:
                    # 只包含key
                    sql_builder.append("SELECT `key` FROM kv_store")

                if key_from != None or key_to != None:
                    sql_builder.append("WHERE 1=1")

                if key_from != None:
                    sql_builder.append("AND `key` >= %s")
                    params.append(key_from)

                if key_to != None:
                    sql_builder.append("AND `key` <= %s")
                    params.append(key_to)

                if reverse:
                    sql_builder.append("ORDER BY `key` DESC")

                sql_builder.append(";")

                sql = " ".join(sql_builder)

                if self.debug:
                    logging.debug("SQL:%s (%s)", sql, params)

                cursor.execute(sql, tuple(params))
                # return cur.execute(sql, tuple(params))
                for item in cursor:
                    # logging.debug("include_value(%s), item:%s", include_value, item)
                    if include_value:
                        if item[1] == None:
                            continue
                        yield self.mysql_to_py(item[0]), self.mysql_to_py(item[1])
                    else:
                        yield self.mysql_to_py(item[0])
            finally:
                self.close_cursor(cursor)

    def CreateSnapshot(self):
        raise NotImplementedError("CreateSnapshot")

    def Write(self, batch, sync=False):
        con = self.get_connection()
        with con:
            cursor = con.cursor(prepared = False)
            try:
                cursor.execute("begin;")
                for key in batch._puts:
                    value = batch._puts[key]
                    self.Put(key, value, cursor=cursor)

                for key in batch._deletes:
                    self.Delete(key, cursor=cursor)
                cursor.execute("commit;")
            finally:
                self.close_cursor(cursor)
