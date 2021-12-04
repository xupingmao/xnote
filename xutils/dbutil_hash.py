# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/04 15:35:23
# @modified 2021/12/04 22:34:24
# @filename dbutil_hash.py

from xutils.dbutil_base import *

class LdbHashTable:
    """基于leveldb的key-value结构"""

    def __init__(self, table_name, user_name = None, key_name = "_key"):
        check_table_name(table_name)

        self.table_name = table_name
        self.key_name = key_name

        self.prefix = table_name
        if user_name != None and user_name != "":
            self.prefix += ":" + user_name

        if self.prefix[-1] != ":":
            self.prefix += ":"

    def _check_key(self, key):
        if not isinstance(key, str):
            raise Exception("LdbHashTable_param_error: expect str key")
        if ":" in key:
            raise Exception("LdbHashTable_param_error: invalid char `:` in key")

    def _check_value(self, obj):
        pass

    def build_key(self, key):
        return self.prefix + key

    def put(self, key, value):
        self._check_key(key)
        self._check_value(value)

        row_key = self.build_key(key)
        put(row_key, value)

    def get(self, key, default_value = None):
        row_key = self.build_key(key)
        return get(row_key, default_value)

    def iter(self, offset = 0, limit = 20, reverse = False, filter_func = None):
        prefix_len = len(self.prefix)
        for key, value in prefix_iter(self.prefix, filter_func = filter_func, 
                offset = offset, limit = limit, reverse = reverse, include_key = True):
            yield key[prefix_len:], value

    def list(self, **kw):
        return list(self.iter(**kw))

    def delete(self, key):
        row_key = self.build_key(key)
        delete(row_key)

    def count(self):
        return count_table(self.prefix)
