# -*- coding:utf-8 -*-
# @author mark
# @since 2022/03/19 10:15:30
# @modified 2022/03/20 21:42:58
# @filename driver_leveldb.py

import leveldb
import logging

from . import driver_interface

class LevelDBImpl(driver_interface.DBInterface):

    log_debug = False

    def __init__(self, path, config_dict=None, **kw):
        """通过leveldbpy来实现leveldb的接口代理，因为leveldb没有提供Windows环境的支持"""
        self._db = leveldb.LevelDB(path, **kw)
        self.config_dict = config_dict
        self.driver_type = "sqlite"

    def Get(self, key):
        try:
            return self._db.Get(key)
        except KeyError:
            return None

    def Put(self, key, value, sync = False):
        return self._db.Put(key, value, sync = sync)

    def Delete(self, key, sync = False):
        return self._db.Delete(key, sync = sync)

    def RangeIter(self, *args, **kw):
        if self.log_debug:
            logging.info("RangeIter(args=%s, kw=%s)", args, kw)
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

