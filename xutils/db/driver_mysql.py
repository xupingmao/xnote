# -*- coding:utf-8 -*-
"""
MySQL驱动

@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-28 12:29:19
@LastEditors  : xupingmao
@LastEditTime : 2022-12-10 23:28:34
@FilePath     : /xnote/xutils/db/driver_mysql.py
@Description  : mysql驱动
"""

import logging
import threading
import time
import mysql.connector
from collections import deque

from xutils.base import Storage


class Holder(threading.local):
    db = None

    def __del__(self):
        if self.db != None:
            self.db.close()


class SqlLoggerInterface:

    def append(self, sql):
        pass


class ConnectionWrapper:

    TTL = 60 # 60秒有效期

    def __init__(self, db, pool):
        self.start_time = time.time()
        self.db = db  # type: mysql.connector.MySQLConnection
        self.is_closed = False
        self.pool = pool

    def __enter__(self):
        return self.db

    def cursor(self, prepared=True):
        return self.db.cursor(prepared=prepared)

    def commit(self):
        return self.db.commit()
    
    def is_expired(self):
        return time.time() - self.start_time > self.TTL
    
    def is_valid(self):
        return self.is_closed == False and not self.is_expired()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pool.append(self)

    def close(self):
        if self.is_closed:
            return
        self.is_closed = True
        self.db.close()
    
    def __del__(self):
        self.close()        


class MySQLKV:

    holder = Holder()
    lock = threading.RLock()

    def __init__(self, *, host=None, port=3306, user=None,
                 password=None, database=None, pool_size=5, sql_logger=None):
        assert pool_size > 0
        self.db_host = host
        self.db_user = user
        self.db_port = port
        self.db_password = password
        self.db_database = database
        self.db_pool_size = pool_size
        self.db_auth_plugin = "mysql_native_password"

        self.debug = True
        self.log_get_profile = True
        self.log_put_profile = True
        self.sql_logger = sql_logger  # type: SqlLoggerInterface
        self.scan_limit = 200  # 扫描的分页大小
        self.pool = deque()
        self.pool_size = 0
        self.debug_pool = True

        self.init()
        RdbSortedSet.init_class(db_instance=self)

    def get_connection(self):
        # 如果不缓存起来, 每次connect和close都会产生网络请求
        wait_con = True
        while wait_con:
            with self.lock:
                if len(self.pool)>0:
                    db = self.pool.popleft()
                    if db.is_valid():
                        if self.debug_pool:
                            logging.debug("复用连接:%s", db.db)
                        return db
                    else:
                        self.pool_size-=1
                        if self.debug_pool:
                            logging.debug("释放连接:%s", db.db)
                        del db
                
                if self.pool_size >= self.db_pool_size:
                    if self.debug_pool:
                        logging.debug("连接已满，等待中...")
                    # 线程池满
                    time.sleep(0.001)
                    continue

                con = self.do_get_connection()
                db = ConnectionWrapper(con, self.pool)

                if self.debug_pool:
                    logging.debug("创建新连接:%s", db.db)

                self.pool_size += 1
                return db

    def do_get_connection(self):
        kw = Storage()
        kw.port = self.db_port
        kw.user = self.db_user
        kw.passwd = self.db_password
        kw.database = self.db_database
        if self.db_pool_size > 0:
            # 使用MySQL连接池
            kw.pool_size = self.db_pool_size
        return mysql.connector.connect(host=self.db_host, **kw)

    def close_cursor(self, cursor):
        cursor.close()

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
                # KEY索引长度并不对key的长度做限制，只是索引最多使用200字节
                # 一个CHAR占用3个字节，索引最多用1000个字节
                cursor.execute("""CREATE TABLE IF NOT EXISTS `kv_store` (
                    `key` blob not null comment '键值对key', 
                    value blob comment '键值对value',
                    PRIMARY KEY (`key`(200))
                ) COMMENT '键值对存储';
                """)
                cursor.execute("""CREATE TABLE IF NOT EXISTS `zset` (
                    `key` varchar(512) not null comment '键值对key',
                    `member` varchar(512) not null comment '成员',
                    `score` decimal(40,20) not null comment '分数',
                    `version` int not null comment '版本',
                    PRIMARY KEY (`key`(100), `member`(100)) ,
                    KEY idx_score(`score`)
                ) COMMENT '有序集合';
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
                for result in cursor.fetchall():
                    return self.mysql_to_py(result[0])
                return None
            finally:
                cost_time = time.time() - start_time
                if self.log_get_profile:
                    logging.debug("GET (%s) cost %.2fms", key, cost_time*1000)

                if self.sql_logger != None:
                    log_info = sql % key + " [%.2fms]" % (cost_time*1000)
                    self.sql_logger.append(log_info)

                self.close_cursor(cursor)

    def Get(self, key):
        return self.doGet(key)

    def BatchGet(self, key_list):
        # type: (list[bytes]) -> dict[bytes, bytes]
        if len(key_list) == 0:
            return {}

        start_time = time.time()
        con = self.get_connection()
        with con:
            cursor = con.cursor(prepared=True)
            try:
                result = dict()
                sql = "SELECT `key`, value FROM kv_store WHERE `key` IN (%s)"
                # mysql.connector不支持传入列表,需要自己处理下
                sql_args = ["%s" for i in key_list]
                sql = sql % ",".join(sql_args)
                cursor.execute(sql, key_list)
                for item in cursor.fetchall():
                    key = self.mysql_to_py(item[0])
                    value = self.mysql_to_py(item[1])
                    result[key] = value
                return result
            finally:
                cost_time = time.time() - start_time
                if self.log_get_profile:
                    logging.debug("BatchGet (%s) cost %.2fms",
                                  key_list, cost_time*1000)

                if self.sql_logger != None:
                    log_info = sql + " [%.2fms]" % (cost_time*1000)
                    self.sql_logger.append(log_info)

                self.close_cursor(cursor)

    def doPut(self, key, value, cursor=None):
        # type: (bytes,bytes,any) -> None
        assert cursor != None

        start_time = time.time()
        select_sql = "SELECT `key` FROM kv_store WHERE `key` = %s"
        insert_sql = "INSERT INTO kv_store (`key`, value) VALUES (%s, %s)"
        update_sql = "UPDATE kv_store SET value=%s WHERE `key` = %s"
        cursor.execute(select_sql, (key, ))
        result = cursor.fetchall()
        if len(result) == 0:
            if self.debug:
                logging.debug("SQL:%s, params:%s", insert_sql, (key, value))

            if self.sql_logger:
                cost_time = time.time() - start_time
                log_info = insert_sql % (key, "?") + \
                    " [%.2fms]" % (cost_time*1000)
                self.sql_logger.append(log_info)

            try:
                cursor.execute(insert_sql, (key, value))
            except:
                logging.info("key(%s) exists, try update", key)
                cursor.execute(update_sql, (value, key))
        else:
            if self.debug:
                logging.debug("SQL:%s, params:%s", update_sql, (key, value))

            if self.sql_logger:
                cost_time = time.time() - start_time
                log_info = update_sql % ("?", key) + \
                    " [%.2fms]" % (cost_time*1000)
                self.sql_logger.append(log_info)

            cursor.execute(update_sql, (value, key))

    def Put(self, key, value, sync=False, cursor=None):
        # type: (bytes,bytes,bool,any) -> None
        """写入Key-Value键值对
        @param {bytes} key
        @param {bytes} value
        """

        start_time = time.time()

        if cursor != None:
            return self.doPut(key, value, cursor=cursor)

        con = self.get_connection()
        with con:
            cursor = con.cursor(prepared=True)
            try:
                self.doPut(key, value, cursor=cursor)
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
        sql = "DELETE FROM kv_store WHERE `key` = %s;"
        if self.debug:
            logging.debug("SQL:%s, params:%s", sql, (key, ))

        if self.sql_logger:
            self.sql_logger.append(sql % (key,))

        cursor.execute(sql, (key, ))

    def doDelete(self, key, sync=False, cursor=None):
        assert cursor != None
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
        limit = self.scan_limit

        with con:
            cursor = con.cursor(prepared=True)
            try:
                sql_builder = []

                if include_value:
                    sql_builder.append("SELECT `key`, value FROM kv_store")
                else:
                    # 只包含key
                    sql_builder.append("SELECT `key` FROM kv_store")

                sql_builder.append("WHERE `key` >= %s AND `key` <= %s")
                if reverse:
                    sql_builder.append("ORDER BY `key` DESC")
                else:
                    sql_builder.append("ORDER BY `key` ASC")

                sql_builder.append("LIMIT %d;" % (limit + 1))
                sql = " ".join(sql_builder)

                has_next = True
                while has_next:
                    params = []
                    if key_from != None:
                        params.append(key_from)
                    else:
                        params.append(b'')

                    if key_to != None:
                        params.append(key_to)
                    else:
                        params.append(b'\xff')

                    if self.debug:
                        logging.debug("SQL:%s (%s)", sql, params)

                    time_before_execute = time.time()
                    cursor.execute(sql, tuple(params))
                    result = cursor.fetchall()

                    if self.sql_logger:
                        cost_time = time.time() - time_before_execute
                        log_info = sql % tuple(
                            params) + " [%.2fms]" % (cost_time*1000)
                        self.sql_logger.append(log_info)

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
        yield from self.RangeIterRaw(*args, **kw)

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

    def Count(self, key_from=b'', key_to=b'\xff'):
        sql = "SELECT COUNT(*) FROM kv_store WHERE `key` >= %s AND `key` <= %s"
        params = (key_from, key_to)

        start_time = time.time()
        con = self.get_connection()
        with con:
            cursor = con.cursor()
            try:
                cursor.execute(sql, params)
                for row in cursor.fetchall():
                    return self.mysql_to_py(row[0])
                return 0
            finally:
                self.close_cursor(cursor)
                if self.debug:
                    logging.debug("SQL:%s, params:%s", sql, params)

                if self.sql_logger:
                    cost_time = time.time() - start_time
                    log_info = sql % params + \
                        " [%.2fms]" % (cost_time*1000)
                    self.sql_logger.append(log_info)


class RdbSortedSet:

    db_instance = None  # type: MySQLKV

    @classmethod
    def init_class(cls, db_instance=None):
        cls.db_instance = db_instance

    def __init__(self, table_name=None):
        self.table_name = table_name

    def mysql_to_str(self, value):
        return bytes(value).decode("utf-8")

    def mysql_to_float(self, value):
        return float(value)

    def put(self, member, score, prefix=""):
        assert isinstance(score, float)

        key = self.table_name + prefix
        with self.db_instance.get_connection() as con:
            cursor = con.cursor(prepared=True)
            params = (score, key, member)
            cursor.execute(
                "UPDATE zset SET `score`=%s, version=version+1 WHERE `key`=%s AND member=%s", params)
            if cursor.rowcount == 0:
                cursor.execute(
                    "INSERT INTO zset (score, `key`, member) VALUES(%s,%s,%s)", params)

    def get(self, member, prefix=""):
        key = self.table_name + prefix
        with self.db_instance.get_connection() as con:
            cursor = con.cursor(prepared=True)
            sql = "SELECT score FROM zset WHERE `key`=%s AND member=%s LIMIT 1"
            cursor.execute(sql, (key, member))
            for item in cursor.fetchall():
                return self.mysql_to_float(item[0])
            return None

    def list_by_score(self, offset=0, limit=20, *, reverse=False, prefix=""):
        sql = "SELECT member, score FROM zset WHERE `key` = %s"
        if reverse:
            sql += " ORDER BY score DESC"
        else:
            sql += " ORDER BY score ASC"

        key = self.table_name + prefix
        sql += " LIMIT %s OFFSET %s" % (limit, offset)
        with self.db_instance.get_connection() as con:
            cursor = con.cursor(prepared=True)
            cursor.execute(sql, (key, ))
            result = []
            for item in cursor.fetchall():
                member = self.mysql_to_str(item[0])
                score = self.mysql_to_float(item[1])
                result.append((member, score))

        return result
