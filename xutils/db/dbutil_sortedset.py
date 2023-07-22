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
        # 大部分场景都不需要支持 float
        # 如果是浮点数，调用方自己转成int
        # self.score_factor = 10**6 # float转int的乘积
        self.prefix = "_rank:" + table_name
        if self.prefix[-1] != ":":
            self.prefix += ":"

    def _format_score(self, score):
        # type: (float|int) -> str
        assert isinstance(score, (float,int))
        score_int = int(score)
        return encode_int(score_int)
    
    def _build_key(self, member="", score=0):
        score_str = self._format_score(score)
        return self.prefix + score_str + ":" + member

    def put(self, member, score, batch = None):
        key = self._build_key(member, score)

        if batch != None:
            batch.put(key, member)
        else:
            db_put(key, member)

    def delete(self, member, score, batch = None):
        key = self._build_key(member, score)

        if batch != None:
            batch.delete(key)
        else:
            db_delete(key)

    def list(self, score=None, offset = 0, limit = 10, reverse = False, include_key = False, key_from=None):
        if score != None:
            prefix = self.prefix + self._format_score(score) + ":"
        else:
            prefix = self.prefix

        return prefix_list(prefix, offset = offset, 
            limit = limit, reverse = reverse, include_key = include_key, key_from=key_from)

class SortedSetItem:

    def __init__(self, member = "", score=0):
        self.member = member
        self.score = score

    def __repr__(self):     
        return dict.__repr__(self.__dict__)

class KvSortedSet(interfaces.SortedSetInterface):

    def __init__(self, table_name):
        # key-value的映射
        self.member_dict = LdbHashTable(table_name)
        # score的排名
        # TODO 考虑把排序放在内存里面
        self.rank = RankTable(table_name)
        self.repair_last_key = None

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
        # type: (dict) -> list[SortedSetItem]
        result = []
        for member in self.rank.list(**kw):
            score = self.get(member)
            result.append(SortedSetItem(member=member, score=score))
        return result

    def repair(self):
        """修复异常数据"""
        offset = 0
        limit = 100
        for key, member in self.rank.list(offset=offset, limit=limit, include_key=True, key_from=self.repair_last_key):
            score = self.get(member)
            if score == None:
                db_delete(key)
                continue

            key2 = self.rank._build_key(member, score)
            if key != key2:
                db_delete(key)
                self.put(member, score)
            
            self.repair_last_key = key
    
    def reset_repair(self):
        self.repair_last_key = None



class RdbSortedSet(interfaces.SortedSetInterface):

    @classmethod
    def init_class(cls, db_instance):
        import web.db
        assert isinstance(db_instance, web.db.DB)
        cls.db_instance = db_instance

    def __init__(self, table_name=""):
        self.table_name = table_name
        check_table_name(table_name)

    def mysql_to_str(self, value):
        if isinstance(value, bytearray):
            return bytes(value).decode("utf-8")
        return value
    
    def mysql_to_int(self, value):
        return int(value)

    def put(self, member, score):
        assert isinstance(score, (int, float))

        key = self.table_name
        vars=dict(key=key,member=member,score=score)
        self.db_instance.query(
            "INSERT INTO kv_zset (score, `key`, member, version) VALUES($score,$key,$member,0) ON DUPLICATE KEY UPDATE score=$score, version=version+1", vars=vars)

    def get(self, member):
        key = self.table_name
        sql = "SELECT score FROM kv_zset WHERE `key`=$key AND member=$member LIMIT 1"
        result_iter = self.db_instance.query(sql, vars=dict(key=key,member=member))
        for item in result_iter:
            return self.mysql_to_int(item.score)
        return None
    
    def delete(self, member=""):
        sql = "DELETE FROM kv_zset WHERE `key`=$key AND member=$member"
        self.db_instance.query(sql, vars=dict(key=self.table_name, member=member))

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
            sql = "SELECT member, score FROM kv_zset WHERE `key` = $key AND score = $score"
        else:
            sql = "SELECT member, score FROM kv_zset WHERE `key` = $key"
        
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
            score = self.mysql_to_int(item.score)
            result.append(SortedSetItem(member=member, score=score))

        return result

class RedisSortedSet(interfaces.SortedSetInterface):
    """TODO 待测试"""    
    
    @classmethod
    def init_class(cls):
        import redis
        cls.redis = redis.Redis(host="localhost",port=6379,db=0)
    
    def __init__(self, table_name=""):
        self.table_name = table_name

    def put(self, member="", score=0):
        self.redis.zadd(self.table_name, {member: score})

    def get(self, member=""):
        return self.redis.zscore(self.table_name, member)

    def delete(self, member=""):
        self.redis.zrem(self.table_name, member)
    
    def list_by_score(self, **kw):
        offset = kw.get("offset", 0)
        limit = kw.get("limit", 20)
        reverse = kw.get("reverse", False)
        score = kw.get("score")
        min = "-inf"
        max = "+inf"
        start = offset

        if score != None:
            min = score
            max = score

        if reverse:
            result = self.redis.zrevrangebyscore(self.table_name, max=max, min=min, start=start, num=limit, withscores=True)
        else: 
            result = self.redis.zrangebyscore(self.table_name, min=min, max=max, start=start, num=limit, withscores=True)
        
        return result
        

def SortedSet(table_name):
    """类似于redis的SortedSet, 但是score仅支持int类型, 浮点数需要调用方自行转换成int类型"""
    if get_driver_name() == "mysql":
        return RdbSortedSet(table_name)
    return KvSortedSet(table_name)
