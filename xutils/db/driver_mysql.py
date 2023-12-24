# -*- coding:utf-8 -*-
"""
MySQL驱动

@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-28 12:29:19
@LastEditors  : xupingmao
@LastEditTime : 2023-12-24 21:51:21
@FilePath     : /xnote/xutils/db/driver_mysql.py
@Description  : mysql驱动
"""

import logging
import threading
import time
from collections import deque
from xutils import interfaces
from xutils.interfaces import SqlLoggerInterface
import web.db

class Holder(threading.local):
    db = None

    def __del__(self):
        if self.db != None:
            self.db.close()

class MySQLKV(interfaces.DBInterface):

    holder = Holder()
    lock = threading.RLock()
    max_value_length = 1024 * 1024 * 5 # 5MB
    long_value_length = 1024 * 10 # 10K

    def __init__(self, *, host=None, port=3306, user=None,
                 password=None, database=None, pool_size=5, 
                 db_instance=None, sql_logger=SqlLoggerInterface()):
        assert isinstance(db_instance, web.db.MySQLDB)
        self.db = db_instance
        
        self.debug = True
        self.log_get_profile = True
        self.log_put_profile = True
        self.sql_logger = sql_logger  # type: SqlLoggerInterface
        self.scan_limit = 200  # 扫描的分页大小
        self.pool = deque()
        self.pool_size = 0
        self.debug_pool = False
        self.driver = ""
        self.driver_type = "mysql"

        try:
            self.init()
        except Exception as e:
            logging.error("mysql driver init failed, host=%s, port=%s, database=%s", host, port, database)
            raise e

    def close_cursor(self, cursor):
        cursor.close()

    def mysql_to_py(self, obj):
        if isinstance(obj, bytearray):
            return bytes(obj)
        return obj

    def init(self):
        # tinyblob 最大长度 255
        # KEY索引长度并不对key的长度做限制，只是索引最多使用200字节
        # 但是如果索引前缀是相同的，会报主键冲突的错误
        # 比如索引长度为5, 存在12345A，插入12345B会报错，插入12346A可以成功
        # 一个CHAR占用3个字节，索引最多用1000个字节
        
        self.db.query("""CREATE TABLE IF NOT EXISTS `kv_store` (
            `key` blob not null comment '键值对key', 
            value longblob comment '键值对value',
            version int not null default 0 comment '版本',
            PRIMARY KEY (`key`(200))
        ) COMMENT '键值对存储';
        """)

    def get_with_version(self, key):
        # type: (bytes) -> tuple[bytes|None, int]
        """通过key读取Value
        @param {bytes} key
        @return {bytes|None} value
        """

        assert isinstance(key, bytes)
        
        start_time = time.time()
        sql = "SELECT value, version FROM kv_store WHERE `key`=$key"
        vars = dict(key=key)
        
        try:
            result_iter = self.db.query(sql, vars=vars)
            for item in result_iter:
                return self.mysql_to_py(item.value), item.version
            return None, 0
        except Exception as e:
            del self.db.ctx.db # 尝试重新连接
            real_sql = self.db.query(sql, vars=vars, _test=True)
            logging.error("SQL:%s", real_sql)
            raise e
        finally:
            cost_time = time.time() - start_time
            
            if self.log_get_profile:
                logging.debug("GET (%s) cost %.2fms", key, cost_time*1000)

            if self.sql_logger != None:
                sql_query = self.db.query(sql, vars=vars, _test=True)
                sql_info = str(sql_query)
                log_info = sql_info + " [%.2fms]" % (cost_time*1000)
                self.sql_logger.append(log_info)

    def doGet(self, key, cursor=None):
        value, version = self.get_with_version(key)
        return value
    
    def Get(self, key=b''):
        value, version = self.get_with_version(key)
        return value

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
            # mysql.connector不支持传入列表,需要自己处理下
            # sql_args = ["%s" for i in key_list]
            # sql = sql % ",".join(sql_args)
            result_iter = self.db.query(sql, vars=vars)
            for item in result_iter:
                key = self.mysql_to_py(item.key)
                value = self.mysql_to_py(item.value)
                result[key] = value
            return result
        finally:
            cost_time = time.time() - start_time
            if self.log_get_profile:
                logging.debug("BatchGet (%s) cost %.2fms",
                                key_list, cost_time*1000)

            if self.sql_logger != None:
                sql_query = self.db.query(sql, vars=vars, _test=True)
                sql_info = str(sql_query)
                log_info = sql_info + " [%.2fms]" % (cost_time*1000)
                self.sql_logger.append(log_info)
    
    def log_sql(self, sql, vars, start_time=0.0, key=None):
        if self.debug:
            sql_query = self.db.query(sql, vars=vars, _test=True)
            logging.debug("SQL:%s", sql_query)

        if self.sql_logger:
            sql_query = self.db.query(sql, vars=vars, _test=True)
            cost_time = time.time() - start_time
            log_info = str(sql_query) + " [%.2fms]" % (cost_time*1000)
            self.sql_logger.append(log_info)

    def put_long_value(self, key, value, sync=False, cursor=None):
        vars = dict(key=key, value=value)
        update_sql = "UPDATE kv_store SET value = $value, version=version+1 WHERE `key` = $key;"
        rows = self.db.query(update_sql, vars=vars)
        self.log_sql(update_sql, vars=vars, key="[Put:Update]")
        assert isinstance(rows, int)
        if rows == 0:
            insert_sql = "INSERT INTO kv_store (`key`, value, version) VALUES ($key,$value,1);"
            self.db.query(insert_sql, vars=vars)
            self.log_sql(insert_sql, vars=vars, key="[Put:Insert]")
            
    def doPut(self, key, value):
        # type: (bytes,bytes) -> None
        if len(value) > self.max_value_length:
            raise interfaces.DatabaseException(code=400, message="value too long")
        
        if len(value) > self.long_value_length:
            return self.put_long_value(key, value)

        start_time = time.time()
        upsert_sql = "INSERT INTO kv_store (`key`, value, version) VALUES ($key, $value, 1) ON DUPLICATE KEY UPDATE value=$value, version=version+1";
        # update_sql = "UPDATE kv_store SET value=$value, version=version+1 WHERE `key` = $key"
        vars = dict(key=key,value=value)

        rowcount = self.db.query(upsert_sql, vars=vars)
        assert isinstance(rowcount, int)
        self.log_sql(upsert_sql, vars, start_time=start_time, key=key)
        assert rowcount > 0

    def Put(self, key, value, sync=False, cursor=None):
        # type: (bytes,bytes,bool,object) -> None
        """写入Key-Value键值对
        @param {bytes} key
        @param {bytes} value
        """

        start_time = time.time()

        try:
            self.doPut(key, value)
        finally:
            cost_time = time.time() - start_time
            if self.log_put_profile:
                logging.debug("Put (%s) cost %.2fms", key, cost_time*1000)
    
    def put_with_version(self, key=b'', value=b'', version=0):
        # type: (bytes,bytes,int) -> int
        start_time = time.time()
        if len(value) > self.max_value_length:
            raise interfaces.DatabaseException(code=400, message="value too long")
        update_sql = "UPDATE kv_store SET value=$value, version=version+1 WHERE `key` = $key AND version=$version"
        insert_sql = "INSERT INTO kv_store (`key`, value, version) VALUES ($key, $value, 1)"
        vars = dict(key=key,value=value,version=version)
        rowcount = self.db.query(update_sql, vars=vars)
        assert isinstance(rowcount, int), "expect int rowcount"
        if rowcount == 0:
            # 数据不存在,执行插入动作
            # 如果这里冲突了，按照默认规则抛出异常
            if version != 0:
                return 0
            # 只有version=0的情况下才能插入
            self.db.query(insert_sql, vars=vars)
            self.log_sql(insert_sql, vars, start_time=start_time, key=key)
            return 1
        else:
            self.log_sql(update_sql, vars, start_time=start_time, key=key)
        return rowcount
    
    def compare_and_put(self, key=b'', value=b'', old_value=None):
        """比较之后再更新,如果old_value=None,则执行insert"""
        # type: (bytes,bytes,bytes|None) -> int
        start_time = time.time()
        if len(value) > self.max_value_length:
            raise interfaces.DatabaseException(code=400, message="value too long")
        update_sql = "UPDATE kv_store SET value=$value, version=version+1 WHERE `key` = $key AND value=$old_value"
        insert_sql = "INSERT INTO kv_store (`key`, value, version) VALUES ($key, $value, 1)"
        vars = dict(key=key,value=value,old_value=old_value)
        
        if old_value == None:
            self.db.query(insert_sql, vars=vars)
            self.log_sql(insert_sql, vars, start_time=start_time, key=key)
            return 1
        
        rowcount = self.db.query(update_sql, vars=vars)
        assert isinstance(rowcount, int), "expect int rowcount"
        self.log_sql(update_sql, vars, start_time=start_time, key=key)
        return rowcount
    
    def Insert(self, key=b'', value=b'', version=0):
        start_time = time.time()
        if len(value) > self.max_value_length:
            raise interfaces.DatabaseException(code=400, message="value too long")
        insert_sql = "INSERT INTO kv_store (`key`, value, version) VALUES ($key, $value, 0)"
        vars = dict(key=key,value=value,version=version)
        try:
            self.db.query(insert_sql, vars=vars)
        finally:
            self.log_sql(insert_sql, vars, start_time=start_time, key=key)

    def doDeleteRaw(self, key=b'', sync=False, cursor=None):
        # type: (bytes, bool, object) -> None
        """删除Key-Value键值对
        @param {bytes} key
        """
        start_time = time.time()
        sql = "DELETE FROM kv_store WHERE `key` = $key;"
        vars = dict(key=key)

        if self.debug:
            sql_query = self.db.query(sql, vars=vars, _test=True)
            logging.debug("SQL:%s", sql_query)

        self.db.query(sql, vars=vars)

        if self.sql_logger:
            sql_query = self.db.query(sql, vars=vars, _test=True)
            sql_info = str(sql_query)
            cost_time = time.time() - start_time
            log_info = sql_info + " [%.2fms]" % (cost_time*1000)
            self.sql_logger.append(log_info)

    def doDelete(self, key, sync=False, cursor=None):
        return self.doDeleteRaw(key, sync, cursor)

    def Delete(self, key=b'', sync=False):
        self.doDeleteRaw(key)

    def BatchDelete(self, keys=[]):
        """批量删除键值对
        :param {list} keys: 键集合
        """
        start_time = time.time()
        sql = "DELETE FROM kv_store WHERE `key` in $keys;"
        vars = dict(keys=keys)

        if self.debug:
            sql_query = self.db.query(sql, vars=vars, _test=True)
            logging.debug("SQL:%s", sql_query)

        self.db.query(sql, vars=vars)

        if self.sql_logger:
            sql_query = self.db.query(sql, vars=vars, _test=True)
            sql_info = str(sql_query)
            cost_time = time.time() - start_time
            log_info = sql_info + " [%.2fms]" % (cost_time*1000)
            self.sql_logger.append(log_info)

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
        limit = self.scan_limit

        sql_builder = []

        if include_value:
            sql_builder.append("SELECT `key`, value FROM kv_store")
        else:
            # 只包含key
            sql_builder.append("SELECT `key` FROM kv_store")

        sql_builder.append("WHERE `key` >= $key_from AND `key` <= $key_to")
        if reverse:
            sql_builder.append("ORDER BY `key` DESC")
        else:
            sql_builder.append("ORDER BY `key` ASC")

        sql_builder.append("LIMIT %d;" % (limit + 1))
        sql = " ".join(sql_builder)

        has_next = True
        while has_next:
            if key_from == None:
                key_from = b''

            if key_to == None:
                key_to = b'\xff'

            vars = dict(key_from=key_from, key_to=key_to)
            if self.debug:
                sql_query = self.db.query(sql, vars=vars, _test=True)
                logging.debug("SQL: %s", sql_query)

            time_before_execute = time.time()
            result_iter = self.db.query(sql, vars=vars)
            result = list(result_iter)

            if self.sql_logger:
                sql_query = self.db.query(sql, vars=vars, _test=True)
                cost_time = time.time() - time_before_execute
                sql_info = str(sql_query)
                log_info = sql_info + " [%.2fms]" % (cost_time*1000)
                self.sql_logger.append(log_info)

            for item in result[:limit]:
                # logging.debug("include_value(%s), item:%s", include_value, item)
                key = self.mysql_to_py(item.key)

                if include_value:
                    if item.value == None:
                        continue
                    yield key, self.mysql_to_py(item.value)
                else:
                    yield key

            if len(result) <= limit:
                break

            last_key = self.mysql_to_py(result[-1].key)
            if reverse:
                key_to = last_key
            else:
                key_from = last_key

    def RangeIter(self, *args, **kw):
        yield from self.RangeIterRaw(*args, **kw)

    def CreateSnapshot(self):
        raise NotImplementedError("CreateSnapshot")

    def Write(self, batch, sync=False):
        assert isinstance(batch, interfaces.BatchInterface)

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
                return self.mysql_to_py(row.amount)
            return 0
        finally:
            if self.debug:
                logging.debug("SQL:%s, key_from=(%r), key_to=(%r)", sql, key_from, key_to)

            if self.sql_logger:
                cost_time = time.time() - start_time
                sql_query = self.db.query(sql, vars=vars, _test=True)
                sql_info = str(sql_query)
                log_info = sql_info + " [%.2fms]" % (cost_time*1000)
                self.sql_logger.append(log_info)
    
    def Increase(self, key=b'', increment=1, start_id=1, max_retry=10):
        """自增方法"""
        assert len(key) > 0, "key can not be empty"
        for retry in range(max_retry):
            old_value, version = self.get_with_version(key)
            if old_value == None:
                value_int = start_id
            else:
                value_int = int(old_value)
                value_int += increment

            value_bytes = str(value_int).encode("utf-8")
            rowcount = self.compare_and_put(key, value_bytes, old_value=old_value)
            if rowcount > 0:
                return value_int
        raise Exception("too many retry")
