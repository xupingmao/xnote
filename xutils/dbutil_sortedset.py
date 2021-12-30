# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/05 11:25:18
# @modified 2021/12/30 22:28:36
# @filename dbutil_sortedset.py

"""【待实现】有序集合，用于各种需要排名的场景，比如
- 最近编辑的笔记
- 访问次数最多的笔记

如果使用了LdbTable的索引功能，其实就不需要这个了
"""

from xutils.dbutil_base import *
from xutils.dbutil_hash import LdbHashTable

register_table("_rank", "排名表")

class RankTable:

    def __init__(self, table_name, user_name = None):
        check_table_name(table_name)
        self.table_name = table_name

        self.prefix = "_rank:" + table_name
        if user_name != None and user_name != "":
            self.prefix += ":" + user_name

        if self.prefix[-1] != ":":
            self.prefix += ":"

    def _format_score(self, score):
        if isinstance(score, int):
            return "%020d" % score
        if isinstance(score, str):
            return "%020s" % score
        raise Exception("_format_score: unsupported score (%r)" % score)

    def put(self, member, score, batch = None):
        score_str = self._format_score(score)
        key = self.prefix + str(score) + ":" + member

        if batch != None:
            batch.put(key, member)
        else:
            put(key, member)

    def delete(self, member, score, batch = None):
        score_str = self._format_score(score)
        key = self.prefix + str(score) + ":" + member

        if batch != None:
            batch.delete(key)
        else:
            delete(key)

    def list(self, offset = 0, limit = 10, reverse = False):
        return prefix_list(self.prefix, offset = offset, limit = limit, reverse = reverse)


class LdbSortedSet:

    def __init__(self, table_name, user_name = None, key_name = "_key"):
        # key-value的映射
        self.member_dict = LdbHashTable(table_name, user_name)
        # score的排名
        self.rank = RankTable(table_name, user_name)

    def put(self, member, score):
        """设置成员分值"""
        with get_write_lock(member):
            batch = create_write_batch()
            old_score = self.member_dict.get(member)
            self.member_dict.put(member, score, batch = batch)
            self.rank.put(member, score, batch = batch)

            if old_score != None:
                self.rank.delete(member, old_score, batch = batch)

            commit_write_batch(batch)

    def get(self, member):
        return self.member_dict.get(member)

    def delete(self, member):
        with get_write_lock(member):
            batch = create_write_batch()
            old_score = self.member_dict.get(member)
            if old_score != None:
                self.member_dict.delete(member, batch = batch)
                self.rank.delete(member, old_score, batch = batch)
            commit_write_batch(batch)

    def list_by_score(self, *args, **kw):
        result = []
        for member in self.rank.list(*args, **kw):
            item = (member, self.get(member))
            result.append(item)
        return result

