# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/05 11:25:18
# @modified 2022/01/24 14:47:38
# @filename dbutil_sortedset.py

"""【待实现】有序集合，用于各种需要排名的场景，比如
- 最近编辑的笔记
- 访问次数最多的笔记

如果使用了LdbTable的索引功能，其实就不需要这个了
"""

import struct
from xutils.db.dbutil_base import *
from xutils.db.dbutil_hash import LdbHashTable

register_table("_rank", "排名表")

class RankTable:

    def __init__(self, table_name):
        check_table_name(table_name)
        self.table_name = table_name

        self.prefix = "_rank:" + table_name
        if self.prefix[-1] != ":":
            self.prefix += ":"

    def _format_score(self, score):
        assert isinstance(score, float)
        buf = struct.pack(">d", score)
        return buf.hex()

    def put(self, member, score, batch = None):
        score_str = self._format_score(score)
        key = self.prefix + score_str + ":" + member

        if batch != None:
            batch.put(key, member)
        else:
            db_put(key, member)

    def delete(self, member, score, batch = None):
        score_str = self._format_score(score)
        key = self.prefix + score_str + ":" + member

        if batch != None:
            batch.delete(key)
        else:
            db_delete(key)

    def list(self, offset = 0, limit = 10, reverse = False):
        return prefix_list(self.prefix, offset = offset, 
            limit = limit, reverse = reverse)


class LdbSortedSet:

    def __init__(self, table_name, key_name = "_key"):
        # key-value的映射
        self.member_dict = LdbHashTable(table_name)
        # score的排名
        self.rank = RankTable(table_name)

    def put(self, member, score):
        """设置成员分值"""
        assert isinstance(score, float)

        with get_write_lock(member):
            batch = create_write_batch()
            old_score = self.member_dict.get(member)
            self.member_dict.put(member, score, batch = batch)
            if old_score != score:
                if old_score != None:
                    self.rank.delete(member, old_score, batch = batch)
                self.rank.put(member, score, batch = batch)
            batch.commit()

    def get(self, member):
        return self.member_dict.get(member)

    def delete(self, member):
        with get_write_lock(member):
            batch = create_write_batch()
            old_score = self.member_dict.get(member)
            if old_score != None:
                self.member_dict.delete(member, batch = batch)
                self.rank.delete(member, old_score, batch = batch)
            batch.commit()

    def list_by_score(self, *args, **kw):
        result = []
        for member in self.rank.list(*args, **kw):
            item = (member, self.get(member))
            result.append(item)
        return result


def SortedSet(table_name):
    if get_driver_name() == "mysql":
        from xutils.db.driver_mysql import RdbSortedSet
        return RdbSortedSet(table_name)
    return LdbSortedSet(table_name)
