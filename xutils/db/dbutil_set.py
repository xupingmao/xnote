# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-07-01 09:03:05
@LastEditors  : xupingmao
@LastEditTime : 2023-07-01 09:56:25
@FilePath     : /xnote/xutils/db/dbutil_set.py
@Description  : 集合的实现
"""
from xutils.db.encode import encode_str, encode_index_value
from xutils.db.dbutil_base import TableInfo
from xutils.db.dbutil_base import db_put, db_delete, count_table, prefix_list, WriteBatchProxy

class KvSetTable:
    """基于Kv存储的集合表
    """

    def __init__(self, table_name = ""):
        first_table = table_name.split(":", maxsplit=1)[0]
        table_info = TableInfo.get_by_name(first_table)
        assert table_info != None

        self.table_name = table_name
        self.prefix = self.table_name + ":"

    def sub_table(self, sub_table=""):
        assert sub_table != ""
        return KvSetTable(self.table_name + ":" + encode_str(sub_table))

    def add(self, *members):
        """添加成员
        :param {list} members: 集合的key
        """
        assert len(members) > 0
        batch = WriteBatchProxy()
        for member in members:
            second_key = encode_index_value(member)
            batch.put(self.prefix + second_key, member)
        batch.commit()

    def remove(self, *members):
        """删除成员
        :param {list} members: 集合的key
        """
        assert len(members) > 0
        batch = WriteBatchProxy()
        for member in members:
            second_key = encode_index_value(member)
            batch.delete(self.prefix + second_key)
        batch.commit()

    
    def batch(self):
        """返回一个批处理对象"""
        return KvSetBatch(self.prefix)

    def list(self, limit=-1):
        return prefix_list(prefix = self.prefix, offset=0, limit=limit)

    def count(self):
        return count_table(self.table_name)


class KvSetBatch:

    def __init__(self, prefix=""):
        self.prefix = prefix
        self._adds = set()
        self._removes = set()
    
    def add(self, member):
        self._adds.add(member)
        self._removes.discard(member)

    def remove(self, member):
        self._adds.discard(member)
        self._removes.add(member)

    def commit(self):
        batch = WriteBatchProxy()
        for member in self._adds:
            batch.put(self.prefix + encode_index_value(member), member)
        for member in self._removes:
            batch.delete(self.prefix + encode_index_value(member))
        batch.commit()
    
    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        if traceback is None:
            self.commit()
    
