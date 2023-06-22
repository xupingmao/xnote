# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-04-15 16:25:49
@LastEditors  : xupingmao
@LastEditTime : 2023-06-22 09:10:02
@FilePath     : /xnote/xutils/db/dbutil_cache.py
@Description  : 数据库缓存

ttl的几种方案
1. 和数据保存到同一个对象
    - 优点：读写只需要一次操作
    - 缺点：
        - 每个对象都要增加一层额外的结构，占用更多空间
        - 需要全量遍历数据用于清理失效数据，如果数据量大清理会占用大量时间
2. 使用单独的ttl表来保存
    - 优点：
        - 便于清理数据
        - 按需设置，占用空间更少
    - 缺点： 读写需要2次
3. ttl同时写入数据库和内存
    - 优点： 兼顾1和2的优点
    - 缺点： 占用更多内存
"""
import time
import random
import logging
from .dbutil_base import db_get, db_put, db_delete, register_table, prefix_iter
from . import encode
from .. import interfaces

register_table("_ttl", "有效期")

class DatabaseCache(interfaces.CacheInterface):

    prefix = "_cache:"
    ttl_prefix = "_ttl:"
    MAX_KEY_LEN = 200

    def _get_dict_value(self, key):
        cache_key = self.prefix + key
        result = db_get(cache_key)
        if not isinstance(result, dict):
            db_delete(cache_key)
            return None
        return result
        
    def get(self, key, default_value=None):
        result = self._get_dict_value(key)
        if result == None:
            return default_value

        expire = result.get("expire", -1)
        if expire < 0:
            return result.get("value")
        
        if expire < time.time():
            # 已失效
            db_delete(self.prefix + key)
            self.delete_ttl(expire, key)
            return default_value
        
        return result.get("value")

    def put(self, key, value, expire = -1,  expire_random = 600):
        assert len(key) < self.MAX_KEY_LEN, "cache key too long"
        assert expire > 0
        expire = int(time.time() + expire)
        expire += random.randint(0, expire_random)
        self.put_ttl(expire, key)
        obj = dict(value = value, expire = expire)
        return db_put(self.prefix + key, obj)
    
    set = put

    def delete(self, key):
        value_dict = self._get_dict_value(key)
        if value_dict == None:
            return
        self.delete_ttl(value_dict.get("expire",-1), key)
        return db_delete(self.prefix + key)
    
    def put_ttl(self, expire, key):
        expire_int = int(expire)
        ttl_key = self.ttl_prefix + encode.encode_int(expire_int) + ":" + key
        db_put(ttl_key, expire)
    
    def delete_ttl(self, expire, key):
        if expire < 0:
            return
        expire_int = int(expire)
        ttl_key = self.ttl_prefix + encode.encode_int(expire_int) + ":" + key
        return db_delete(ttl_key)

    def clear_expired(self, limit=100):
        for key, value in prefix_iter(self.ttl_prefix, limit=limit, include_key=True):
            decoder = encode.KeyDecoder(key)
            ttl_prefix = decoder.pop_left()
            expire = decoder.pop_left()
            user_key = decoder.rest()
            expire_int = int(value)
            if expire_int >= time.time():
                # 还未超时
                break
            # if user_key != "":
            #     self.delete(user_key)
            logging.info("Delete: (%s)", user_key)