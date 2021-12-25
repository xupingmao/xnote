# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/05 11:25:18
# @modified 2021/12/25 22:45:38
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

    def put(self, member, score):
        score_str = self._format_score(score)
        put(self.prefix + str(score) + ":" + member, member)

    def delete(self, member, score):
        score_str = self._format_score(score)
        delete(self.prefix + str(score) + ":" + member)

    def list(self, offset = 0, limit = 10, reverse = False):
        return prefix_list(self.prefix, offset = offset, limit = limit, reverse = reverse)


class LdbSortedSet:

    def __init__(self, table_name, user_name = None, key_name = "_key"):
        # key-value的映射
        self.member_dict = LdbHashTable(table_name, user_name)
        # score的排名
        self.rank = RankTable(table_name, user_name)

    def create_redo_log(self, member, score):
        # TODO: 重做日志，用于故障恢复
        pass

    def delete_redo_log(self, log_id):
        # TODO: 重做日志，用于故障恢复
        pass

    def put(self, member, score):
        """设置成员分值"""
        with get_write_lock(member):
            log_id = self.create_redo_log(member, score)
            old_score = self.member_dict.get(member)
            self.member_dict.put(member, score)
            self.rank.put(member, score)

            if old_score != None:
                self.rank.delete(member, old_score)
            self.delete_redo_log(log_id)

    def get(self, member):
        return self.member_dict.get(member)

    def delete(self, member):
        with get_write_lock(member):
            old_score = self.member_dict.get(member)
            if old_score != None:
                self.member_dict.delete(member)
                self.rank.delete(member, old_score)

    def list_by_score(self, *args, **kw):
        result = []
        for member in self.rank.list(*args, **kw):
            item = (member, self.get(member))
            result.append(item)
        return result

def _zadd(key, score, member):
    # step1. write log
    # step2. delete zscore:key:score
    # step3. write zmember:key:member = score
    # step4. write zscore:key:score = [key1, key2]
    # step5. delete log
    obj = get(key)
    # print("zadd %r %r" % (member, score))
    if obj != None:
        obj[member] = score
        put(key, obj)
    else:
        obj = dict()
        obj[member] = score
        put(key, obj)

def _zrange(key, start, stop):
    """zset分片，不同于Python，这里是左右包含，包含start，包含stop，默认从小到大排序
    :arg int start: 从0开始，负数表示倒数
    :arg int stop: 从0开始，负数表示倒数
    TODO 优化排序算法，使用有序列表+哈希表
    """
    obj = get(key)
    if obj != None:
        items = obj.items()
        length = len(items)

        if stop < 0:
            stop += length + 1
        if start < 0:
            start += length + 1

        sorted_items = sorted(items, key = lambda x: x[1])
        sorted_keys = [k[0] for k in sorted_items]
        if stop < start:
            # 需要逆序
            stop -= 1
            start += 1
            found = sorted_keys[stop: start]
            found.reverse()
            return found
        return sorted_keys[start: stop]
    return []

def _zcount(key):
    obj = get(key)
    if obj != None:
        return len(obj)
    return 0

def _zscore(key, member):
    obj = get(key)
    if obj != None:
        return obj.get(member)
    return None

def _zrem(key, member):
    obj = get(key)
    if obj != None:
        if member in obj:
            del obj[member]
            put(key, obj)
            return 1
    return 0
