# -*- coding:utf-8 -*-
# @author mark
# @since 2022/03/20 14:43:04
# @modified 2022/04/23 16:13:02
# @filename driver_lmdb.py

import lmdb
import logging
import threading

from xutils import textutil
from xutils.base import Storage
from xutils.db.encode import convert_bytes_to_object, convert_object_to_bytes, encode_int8_to_bytes


# 用于写操作的加锁，所以在多进程或者分布式环境中写操作是不安全的
_lock = threading.RLock()

class LmdbKV:

    def __init__(self, db_dir, debug=True, map_size=1024**3):
        self.env = lmdb.open(db_dir, map_size=map_size)
        self.debug = debug

    def Get(self, key):
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

            for key in batch_proxy._deletes:
                tx.delete(key)

    def Stat(self):
        return self.env.stat()


class LmdbEnhancedKV:

    def __init__(self, *args, **kw):
        self.kv = LmdbKV(*args, **kw)
        self.max_key_size = self.kv.env.max_key_size() - 10

    def get_large_key_prefix(self, key):
        return key[:self.max_key_size] + b":"

    def make_large_key(self, key):
        prefix = self.get_large_key_prefix(key)
        key_from = prefix
        key_to = prefix + b"\xff"
        index = 0

        for exist_key, value in self.kv.RangeIter(key_from=key_from, key_to=key_to, include_value=True):
            value_obj = convert_bytes_to_object(value)
            if value_obj.get("_key") == key:
                return exist_key, value_obj.get("_idx")
            index = value_obj.get("_idx") + 1

        # TODO 还要考虑排序的问题
        return prefix + encode_int8_to_bytes(index), index

    def Get(self, key):
        if len(key) >= self.max_key_size:
            prefix = self.get_large_key_prefix(key)
            key_from = prefix
            key_to = prefix + b"\xff"
            key_str = key.decode("utf-8")

            for tmp_key, value in self.kv.RangeIter(key_from=key_from, key_to=key_to, include_value=True):
                value_obj = convert_bytes_to_object(value)
                if value_obj.get("_key") == key_str:
                    return value_obj.get("_value").encode("utf-8")
            return None

        return self.kv.Get(key)

    def Put(self, key, value, sync=False):
        if len(key) >= self.max_key_size:
            logging.warning("key长度(%d)超过限制(%d)", len(key), self.max_key_size)
            real_key, idx = self.make_large_key(key)
            value_obj = Storage(_key=key, _value=value, _idx=idx)
            value = convert_object_to_bytes(value_obj)
            key = real_key

        return self.kv.Put(key, value)

    def Delete(self, key, sync=False):
        if len(key) >= self.max_key_size:
            prefix = self.get_large_key_prefix(key)
            key_from = prefix
            key_to = prefix + b"\xff"
            key_str = key.decode("utf-8")
            for tmp_key, value in self.kv.RangeIter(key_from=key_from, key_to=key_to, include_value=True):
                value_obj = convert_bytes_to_object(value)
                if value_obj.get("_key") == key_str:
                    return self.kv.Delete(tmp_key)
            return None
        return self.kv.Delete(key, sync)

    def RangeIter(self, *args, **kw):
        raise Exception("当前实现不支持按顺序遍历")


class LmdbEnhancedKV2:

    def __init__(self, *args, **kw):
        self.kv = LmdbKV(*args, **kw)
        self.max_key_size = self.kv.env.max_key_size()

    def get_large_key_prefix(self, key):
        return key[:self.max_key_size]

    def create_new_key(self, key):
        for i in range(10):
            new_key = "_long_key:" + textutil.create_uuid()
            new_key = new_key.encode("utf-8")
            if self.kv.Get(new_key) == None:
                return new_key
        raise Exception("create_new_key: too many retries!")

    def get_value_dict(self, prefix):
        value = self.kv.Get(prefix)
        if value is None:
            return dict()
        else:            
            value_dict = convert_bytes_to_object(value)
            result = dict()
            for key in value_dict:
                value = value_dict[key]
                result[key.encode("utf-8")] = value.encode("utf-8")
            return result

    def save_value_dict(self, prefix, value_dict):
        if len(value_dict) == 0:
            self.kv.Delete(prefix)
            return
        data = dict()
        for key in value_dict:
            value = value_dict[key]
            data[key.decode("utf-8")] = value.decode("utf-8")
        self.kv.Put(prefix, convert_object_to_bytes(data))

    def Get(self, key):
        if len(key) >= self.max_key_size:
            prefix = self.get_large_key_prefix(key)
            value_dict = self.get_value_dict(prefix)
            for fullkey in value_dict:
                if fullkey == key:
                    newkey = value_dict[fullkey]
                    return self.kv.Get(newkey)

        return self.kv.Get(key)

    def Put(self, key, value, sync=False):
        if len(key) >= self.max_key_size:
            logging.warning("key长度(%d)超过限制(%d)", len(key), self.max_key_size)
            prefix = self.get_large_key_prefix(key)
            with _lock:
                value_dict = self.get_value_dict(prefix)
                new_key = value_dict.get(key)
                if new_key != None:
                    self.kv.Put(new_key, value, sync)
                else:
                    new_key = self.create_new_key(key)
                    value_dict[key] = new_key
                    self.kv.Put(new_key, value, sync)
                    self.save_value_dict(prefix, value_dict)
                    return
        return self.kv.Put(key, value, sync)

    def Delete(self, key, sync=False):
        if len(key) >= self.max_key_size:
            prefix = self.get_large_key_prefix(key)
            with _lock:
                value_dict = self.get_value_dict(prefix)
                new_key = value_dict.get(key)
                if new_key != None:
                    self.kv.Delete(new_key, sync)
                    del value_dict[key]
                    self.save_value_dict(prefix, value_dict)
                return
        return self.kv.Delete(key, sync)

    def RangeIter(self, *args, **kw):
        include_value = kw.get("include_value", True)
        if include_value:
            for key, value in self.kv.RangeIter(*args, **kw):
                if len(key) >= self.max_key_size:
                    prefix = self.get_large_key_prefix(key)
                    value_dict = self.get_value_dict(prefix)
                    # 必须要保证key的迭代顺序
                    for fullkey in sorted(value_dict.keys()):
                        new_key = value_dict[fullkey]
                        yield fullkey, self.kv.Get(new_key)
                else:
                    yield key, value
        else:
            for key in self.kv.RangeIter(*args, **kw):
                if len(key) >= self.max_key_size:
                    prefix = self.get_large_key_prefix(key)
                    value_dict = self.get_value_dict(prefix)
                    # 必须要保证key的迭代顺序
                    for fullkey in sorted(value_dict.keys()):
                        yield fullkey
                else:
                    yield key
