# -*- coding:utf-8 -*-
# @author mark
# @since 2022/03/19 10:15:30
# @modified 2022/03/19 10:18:02
# @filename driver_leveldb.py

import leveldb

class LevelDBImpl:

    def __init__(self, path, **kw):
        """通过leveldbpy来实现leveldb的接口代理，因为leveldb没有提供Windows环境的支持"""
        self._db = leveldb.LevelDB(path, **kw)

    def Get(self, key):
        return self._db.Get(key)

    def Put(self, key, value, sync = False):
        return self._db.Put(key, value, sync = sync)

    def Delete(self, key, sync = False):
        return self._db.Delete(key, sync = sync)

    def RangeIter(self, *args, **kw):
        return self._db.RangeIter(*args, **kw)

    def CreateSnapshot(self):
        return self._db.CreateSnapshot()

    def Write(self, batch_proxy, sync = False):
        """执行批量操作"""
        batch = leveldb.WriteBatch()
        for key in batch_proxy._puts:
            value = batch_proxy._puts[key]
            batch.Put(key, value)
        for key in batch_proxy._deletes:
            batch.Delete(key)
        return self._db.Write(batch, sync)

