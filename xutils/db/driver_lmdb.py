# -*- coding:utf-8 -*-
# @author mark
# @since 2022/03/20 14:43:04
# @modified 2022/04/23 16:13:02
# @filename driver_lmdb.py

import lmdb
import logging
import threading
from xutils import interfaces
from xutils.db.encode import convert_bytes_dict_to_bytes, convert_bytes_to_dict


# 用于写操作的加锁，所以在多进程或者分布式环境中写操作是不安全的
_lock = threading.RLock()

class LmdbKV(interfaces.DBInterface):

    def __init__(self, db_dir, debug=True, map_size=1024**3, config_dict=None):
        self.env = lmdb.open(db_dir, map_size=map_size)
        self.debug = debug
        self.config_dict = config_dict
        self.driver_type = "lmdb"

    def Get(self, key):
        # type: (bytes) -> bytes
        """通过key读取Value
        @param {bytes} key
        @return {bytes|None} value
        """
        with self.env.begin() as tx:
            return tx.get(key)

    def Put(self, key, value, sync=False):
        """写入Key-Value键值对
        @param {bytes} key
        @param {bytes} value
        """
        if self.debug:
            logging.debug("Put: key(%s), value(%s)", key, value)

        if len(key) > self.env.max_key_size():
            raise Exception("key长度(%d)超过限制(%d)" %
                            (len(key), self.env.max_key_size()))

        with self.env.begin(write=True) as tx:
            tx.put(key, value)

    def Delete(self, key, sync=False):
        """删除Key-Value键值对
        @param {bytes} key
        """

        if self.debug:
            logging.debug("Delete: key(%s)", key)

        with self.env.begin(write=True) as tx:
            tx.delete(key)

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
        if self.debug:
            logging.debug("RangeIter: key_from(%s), key_to(%s), reverse(%s)",
                          key_from, key_to, reverse)

        if reverse:
            for item in self.RangeIter_reverse(key_from, key_to, include_value):
                yield item
            return

        with self.env.begin() as tx:
            with tx.cursor() as cur:
                if key_from != None:
                    has_value = cur.set_range(key_from)
                else:
                    has_value = cur.first()

                if has_value:
                    if key_to != None and cur.key() > key_to:
                        return  # 越界
                    if include_value:
                        yield cur.item()
                    else:
                        yield cur.key()

                while cur.next():
                    if key_to != None and cur.key() > key_to:
                        return  # 越界
                    if include_value:
                        yield cur.item()
                    else:
                        yield cur.key()

    def RangeIter_reverse(self, key_from=None, key_to=None,
                          include_value=True):
        """反向遍历数据"""
        with self.env.begin() as tx:
            with tx.cursor() as cur:
                if key_to != None:
                    has_value = cur.set_range(key_to)  # cur >= key_to
                    if not has_value:  # 不存在>=key_to的值，移动到最后一位
                        has_value = cur.last()
                else:
                    has_value = cur.last()  # 各种可能性

                if not has_value:
                    return

                if key_to != None and cur.key() > key_to:  # cur > key_to 需要回溯1位
                    has_value = cur.prev()

                if not has_value:
                    return

                if key_from != None and cur.key() < key_from:
                    # 越界了
                    return

                if include_value:
                    yield cur.item()
                else:
                    yield cur.key()

                while cur.prev():
                    if key_from != None and cur.key() < key_from:
                        # 越界了
                        return
                    if include_value:
                        yield cur.item()
                    else:
                        yield cur.key()

    def CreateSnapshot(self):
        return self

    def Write(self, batch_proxy, sync=False):
        with self.env.begin(write=True) as tx:
            for key in batch_proxy._puts:
                value = batch_proxy._puts[key]
                tx.put(key, value)

            for key in batch_proxy._inserts:
                value = batch_proxy._inserts[key]
                old_value = tx.get(key)
                if old_value != None:
                    raise interfaces.new_duplicate_key_exception(key)
                tx.put(key, value)
                
            for key in batch_proxy._deletes:
                tx.delete(key)

    def Stat(self):
        return self.env.stat()

class LmdbEnhancedKV(interfaces.DBInterface):

    """Lmdb增强版，用于解决key长度限制的问题，之所以不重新编译是基于以下考虑
    1. 直接在上层封装使用起来更方便
    2. 超长key本身不是一个常见的案例，并且也不是好的设计
    """

    def __init__(self, *args, **kw):
        self.kv = LmdbKV(*args, **kw)
        self.max_key_size = self.kv.env.max_key_size()

    def get_large_key_prefix(self, key):
        # type: (bytes)->bytes
        return key[:self.max_key_size]

    def get_value_dict(self, prefix, tx=None):
        if tx != None:
            value = tx.get(prefix)
        else:
            value = self.kv.Get(prefix)
        return convert_bytes_to_dict(value)

    def save_value_dict(self, tx, prefix, value_dict):
        if len(value_dict) == 0:
            tx.delete(prefix)
            return
        data_bytes = convert_bytes_dict_to_bytes(value_dict)
        tx.put(prefix, data_bytes)

    def Get(self, key):
        if len(key) >= self.max_key_size:
            prefix = self.get_large_key_prefix(key)
            value_dict = self.get_value_dict(prefix)
            return value_dict.get(key)

        return self.kv.Get(key)

    def Put(self, key, value, sync=False):
        with self.kv.env.begin(write=True) as tx:
            return self.doPut(tx, key, value, sync)

    def doPut(self, tx, key, value, sync=False): 
        # type: (object, bytes, bytes, bool) -> object
        if len(key) >= self.max_key_size:
            logging.warning("key长度(%d)超过限制(%d)", len(key), self.max_key_size)
            prefix = self.get_large_key_prefix(key)
            with _lock:
                value_dict = self.get_value_dict(prefix, tx=tx)
                value_dict[key] = value
                self.save_value_dict(tx, prefix, value_dict)
                return
        return tx.put(key, value)

    def doDelete(self, tx, key, sync=False):
        # type: (object, bytes, bool) -> object
        if len(key) >= self.max_key_size:
            prefix = self.get_large_key_prefix(key)
            with _lock:
                value_dict = self.get_value_dict(prefix, tx=tx)
                if key in value_dict:
                    del value_dict[key]
                self.save_value_dict(tx, prefix, value_dict)
                return
        return tx.delete(key)
    
    def Delete(self, key, sync=False):
        with self.kv.env.begin(write=True) as tx:
            return self.doDelete(tx, key, sync)
    
    def RangeIterRaw(self, *args, **kw):
        yield from self.kv.RangeIter(*args, **kw)

    def RangeIter(self, *args, **kw):
        include_value = kw.get("include_value", True)
        reverse = kw.get("reverse", False)

        if include_value:
            for key, value in self.kv.RangeIter(*args, **kw):
                if len(key) >= self.max_key_size:
                    value_dict = self.get_value_dict(key)
                    # 必须要保证key的迭代顺序
                    for fullkey in sorted(value_dict.keys(), reverse=reverse):
                        yield fullkey, value_dict[fullkey]
                else:
                    yield key, value
        else:
            for key in self.kv.RangeIter(*args, **kw):
                if len(key) >= self.max_key_size:
                    value_dict = self.get_value_dict(key)
                    # 必须要保证key的迭代顺序
                    for fullkey in sorted(value_dict.keys(), reverse=reverse):
                        yield fullkey
                else:
                    yield key

    def Write(self, batch_proxy, sync=False):
        with self.kv.env.begin(write=True) as tx:
            for key in batch_proxy._puts:
                value = batch_proxy._puts[key]
                self.doPut(tx, key, value)
            
            for key in batch_proxy._inserts:
                value = batch_proxy._inserts[key]
                old_value = self.Get(key)
                if old_value != None:
                    raise interfaces.new_duplicate_key_exception(key)
                self.doPut(tx, key, value)

            for key in batch_proxy._deletes:
                self.doDelete(tx, key, sync)

