# -*- coding:utf-8 -*-
# @author mark
# @since 2022/03/19 10:03:49
# @modified 2022/03/19 10:10:34
# @filename driver_leveldbpy.py

import leveldbpy

class LevelDBProxy:

    def __init__(self, path, snapshot = None, 
            max_open_files = 1000,
            block_cache_size = None, 
            write_buffer_size = None):
        """通过leveldbpy来实现leveldb的接口代理，因为leveldb没有提供Windows环境的支持"""

        if snapshot != None:
            self._db = snapshot
        else:
            self._db = leveldbpy.DB(path.encode("utf-8"), 
                create_if_missing = True, 
                block_cache_size = block_cache_size,
                max_open_files = max_open_files)

    def Get(self, key):
        return self._db.get(key)

    def Put(self, key, value, sync = False):
        return self._db.put(key, value, sync = sync)

    def Delete(self, key, sync = False):
        return self._db.delete(key, sync = sync)

    def RangeIter(self, key_from = None, key_to = None, 
            reverse = False, include_value = True, 
            fill_cache = False):
        """返回区间迭代器
        @param {str}  key_from       开始的key（包含）
        @param {str}  key_to         结束的key（包含）
        @param {bool} reverse        是否反向查询
        @param {bool} include_value  是否包含值
        """
        if include_value:
            keys_only = False
        else:
            keys_only = True

        iterator = self._db.iterator(keys_only = keys_only)

        return iterator.RangeIter(key_from, key_to, 
            include_value = include_value, reverse = reverse)

    def CreateSnapshot(self):
        return LevelDBProxy(snapshot = self._db.snapshot())

    def Write(self, batch_proxy, sync = False):
        """执行批量操作"""
        batch = leveldbpy.WriteBatch()
        for key in batch_proxy._puts:
            value = batch_proxy._puts[key]
            batch.put(key, value)
        for key in batch_proxy._deletes:
            batch.delete(key)
        return self._db.write(batch, sync)

