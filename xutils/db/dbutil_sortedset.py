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

from xutils.db.dbutil_base import *
from xutils.db.dbutil_hash import LdbHashTable
from xutils.db.encode import encode_int

register_table("_rank", "排名表")

class RankTable:

    def __init__(self, table_name):
        check_table_name(table_name)
        self.table_name = table_name
        self.score_factor = 10**6 # float转int的乘积
        self.prefix = "_rank:" + table_name
        if self.prefix[-1] != ":":
            self.prefix += ":"

    def _format_score(self, score):
        # type: (float|int) -> str
        assert isinstance(score, (float,int))
        score_int = int(score * self.score_factor)
        return encode_int(score_int)

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

    def list(self, score=None, offset = 0, limit = 10, reverse = False):
        if score != None:
            prefix = self.prefix + self._format_score(score) + ":"
        else:
            prefix = self.prefix

        return prefix_list(prefix, offset = offset, 
            limit = limit, reverse = reverse)

class SortedSetItem:

    def __init__(self, member = "", score=0.0):
        self.member = member
        self.score = score

    def __repr__(self):     
        return dict.__repr__(self.__dict__)

class LdbSortedSet:

    def __init__(self, table_name):
        # key-value的映射
        self.member_dict = LdbHashTable(table_name)
        # score的排名
        # TODO 考虑把排序放在内存里面
        self.rank = RankTable(table_name)

    def put(self, member, score):
        """设置成员分值"""
        assert isinstance(score, (float, int))

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

    def list_by_score(self, **kw):
        result = []
        for member in self.rank.list(**kw):
            score = self.get(member)
            result.append(SortedSetItem(member=member, score=score))
        return result



class RdbSortedSet:

    @classmethod
    def init_class(cls, db_instance):
        import web.db
        assert isinstance(db_instance, web.db.DB)
        cls.db_instance = db_instance

    def __init__(self, table_name=""):
        self.table_name = table_name

    def mysql_to_str(self, value):
        if isinstance(value, bytearray):
            return bytes(value).decode("utf-8")
        return value

    def mysql_to_float(self, value):
        return float(value)

    def put(self, member, score, prefix=""):
        assert isinstance(score, float)

        key = self.table_name + prefix
        vars=dict(key=key,member=member,score=score)
        rowcount = self.db_instance.query(
            "UPDATE zset SET `score`=$score, version=version+1 WHERE `key`=$key AND member=$member", vars=vars)
        if rowcount == 0:
            self.db_instance.query(
                "INSERT INTO zset (score, `key`, member, version) VALUES($score,$key,$member,0)", vars=vars)

    def get(self, member, prefix=""):
        key = self.table_name + prefix
        sql = "SELECT score FROM zset WHERE `key`=$key AND member=$member LIMIT 1"
        result_iter = self.db_instance.query(sql, vars=dict(key=key,member=member))
        for item in result_iter:
            return self.mysql_to_float(item.score)
        return None

    def list_by_score(self, **kw):
        """通过score查询列表
        :param offset=0: 下标
        :param limit=20: 数量
        :param reverse=False: 是否反向查询
        :param score=None: 指定score查询
        """
        prefix = kw.get("prefix", "")
        offset = kw.get("offset", 0)
        limit = kw.get("limit", 20)
        reverse = kw.get("reverse", False)
        score = kw.get("score")

        if score != None:
            sql = "SELECT member, score FROM zset WHERE `key` = $key AND score = $score"
        else:
            sql = "SELECT member, score FROM zset WHERE `key` = $key"
        
        if reverse:
            sql += " ORDER BY score DESC"
        else:
            sql += " ORDER BY score ASC"

        key = self.table_name + prefix
        sql += " LIMIT %s OFFSET %s" % (limit, offset)
        result_iter = self.db_instance.query(sql, vars=dict(key=key, score=score))
        result = []
        for item in result_iter:
            member = self.mysql_to_str(item.member)
            score = self.mysql_to_float(item.score)
            result.append(SortedSetItem(member=member, score=score))

        return result


def SortedSet(table_name):
    if get_driver_name() == "mysql":
        return RdbSortedSet(table_name)
    return LdbSortedSet(table_name)
