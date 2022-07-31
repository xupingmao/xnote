# -*- coding:utf-8 -*-
"""
开发中...

@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-28 12:29:19
@LastEditors  : xupingmao
@LastEditTime : 2022-07-31 20:47:13
@FilePath     : /xnote/xutils/db/driver_mysql.py
@Description  : mysql驱动
"""

import threading
import pymysql


class Holder(threading.local):
    db = None

    def __del__(self):
        if self.db != None:
            self.db.close()


class MySQLKv:

    holder = Holder()

    def __init__(self, *, host=None, user=None, password=None, database=None):
        self.db_host = host
        self.db_user = user
        self.db_password = password
        self.db_database = database

    def get_connection(self):
        if self.holder.db == None:
            self.holder.db = pymysql.connect(host=self.db_host, user=self.db_user, password=self.db_password,
                                             database=self.db_database)

        return self.holder.db

    def Get(self, key):
        """通过key读取Value
        @param {bytes} key
        @return {bytes|None} value
        """
        con = self.get_connection()
        with con:
            with con.cursor() as cursor:
                sql = "SELECT value FROM kv_store WHERE `key`=%s"
                cursor.execute(sql, (key, ))
                result = cursor.fetchone()
                if len(result) > 0:
                    return result[0][0]
                else:
                    return None

    def Put(self, key, value, sync=False):
        """写入Key-Value键值对
        @param {bytes} key
        @param {bytes} value
        """
        con = self.get_connection()
        with con:
            with con.cursor() as cursor:
                sql = "INSERT INTO kv_store (`key`, value) VALUES (%s, %s) ON DUPLICATE UPDATE value = %s"
                cursor.execute(sql, (key, value, value))
                con.commit()


    def Delete(self, key, sync=False):
        """删除Key-Value键值对
        @param {bytes} key
        """
        con = self.get_connection()
        with con:
            with con.cursor() as cursor:
                sql = "DELETE FROM kv_store (`key`, value) WHERE `key` = %s"
                cursor.execute(sql, (key, ))
                con.commit()

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
        raise NotImplementedError("RangeIter")

    def CreateSnapshot(self):
        raise NotImplementedError("CreateSnapshot")

    def Write(self, batch_proxy, sync=False):
        raise NotImplementedError("Write")
