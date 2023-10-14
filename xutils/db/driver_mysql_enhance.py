# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-10-01 21:15:02
@LastEditors  : xupingmao
@LastEditTime : 2023-10-14 17:21:33
@FilePath     : /xnote/xutils/db/driver_mysql_enhance.py
@Description  : 支持长key, 废弃了, 不推荐使用
"""
import pdb
from xutils.db import encode
from xutils.db.driver_mysql import MySQLKV

class EnhancedMySQLKV(MySQLKV):

    def init(self):
        super().init()
        self.max_key_len = 200

    def doPutRaw(self, key, value, cursor=None):
        assert len(key) <= self.max_key_len
        return super().doPut(key, value)

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
                    value_bytes = super().Get(key)
                    value_dict = encode.convert_bytes_to_dict(value_bytes)
                    # 必须要保证key的迭代顺序
                    for fullkey in sorted(value_dict.keys(), reverse=reverse):
                        yield fullkey
                else:
                    yield key

    def doDeleteLongNoLock(self, key, cursor):
        short_key = key[:self.max_key_len]
        data_bytes = self.doGet(short_key, cursor=cursor)
        assert isinstance(data_bytes, bytes)
        data_dict = encode.convert_bytes_to_dict(data_bytes)
        if key in data_dict:
            del data_dict[key]

        if len(data_dict) == 0:
            self.doDelete(short_key, cursor=cursor)
        else:
            self.doPutRaw(
                short_key, encode.convert_bytes_dict_to_bytes(data_dict), cursor)

    def Delete(self, key, sync=False, cursor=None):
        if len(key) >= self.max_key_len:
            with self.lock:
                self.doDeleteLongNoLock(key, cursor)
        else:
            return self.doDelete(key, sync, cursor)

    def doPut(self, key, value, cursor=None):
        if len(key) >= self.max_key_len:
            short_key = key[:self.max_key_len]
            with self.lock:
                data_bytes = self.doGet(short_key, cursor=cursor)
                data_dict = encode.convert_bytes_to_dict(data_bytes)
                data_dict[key] = value
                self.doPutRaw(
                    short_key, encode.convert_bytes_dict_to_bytes(data_dict), cursor)
        else:
            return self.doPutRaw(key, value, cursor)

    def Get(self, key):
        if len(key) >= self.max_key_len:
            short_key = key[:self.max_key_len]
            data_bytes = super().Get(short_key)
            data_dict = encode.convert_bytes_to_dict(data_bytes)
            return data_dict.get(key)
        else:
            return super().Get(key)
