# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-04-15 16:25:49
@LastEditors  : xupingmao
@LastEditTime : 2023-07-01 10:53:40
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
from xutils.db import encode
from xutils import interfaces


register_table("_ttl", "有效期")
register_table("_cache", "缓存")

class DatabaseCache(interfaces.CacheInterface):

    prefix = "_cache:"
    MAX_KEY_LEN = 200

    def __init__(self):
        self.last_scan_key = ""

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
            return default_value
        
        return result.get("value")

    def put(self, key, value, expire = -1,  expire_random = 600):
        assert len(key) < self.MAX_KEY_LEN, "cache key too long"
        assert expire > 0
        expire = int(time.time() + expire)
        expire += random.randint(0, expire_random)
        # TODO 失效信息记录到内存中
        obj = dict(value = value, expire = expire)
        return db_put(self.prefix + key, obj)
    
    set = put

    def delete(self, key):
        value_dict = self._get_dict_value(key)
        if value_dict == None:
            return
        return db_delete(self.prefix + key)

    def clear_expired(self, limit=1000):
        key_from = None
        if self.last_scan_key != "":
            key_from = self.last_scan_key
        
        count = 0
        for key, value in prefix_iter(self.prefix, limit=limit, include_key=True, key_from=key_from):
            key_decoder = encode.KeyDecoder(key)
            key_decoder.pop_left() # _cache: 前缀
            biz_key = key_decoder.rest()
            self.get(biz_key)
            self.last_scan_key = key
            count += 1
        
        if count < limit:
            # 扫描完成, 重置last_scan_key
            self.last_scan_key = ""
        
        logging.info("count=%s, last_scan_key=%s", count, self.last_scan_key)
        return count

    def get_expire(self, key):
        dict_value = self._get_dict_value(key)
        if dict_value == None:
            return 0
        return dict_value.get("expire", 0)
    
    def list_keys(self, offset=0, limit=20):
        iter = prefix_iter(self.prefix, offset=offset, limit=limit, include_key=True)
        result = []
        for key, value in iter:
            prefix, cache_key = key.split(":",1)
            result.append(cache_key)
        return result