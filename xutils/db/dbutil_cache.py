# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-04-15 16:25:49
@LastEditors  : xupingmao
@LastEditTime : 2023-04-15 16:58:29
@FilePath     : /xnote/xutils/db/dbutil_cache.py
@Description  : 数据库缓存
"""
import time
import json
import random
from .dbutil_base import db_get, db_put
from . import driver_interface

class CacheImpl(driver_interface.CacheInterface):

    prefix = "_cache:"

    def get(self, key):
        result = db_get(self.prefix + key)
        if result == None:
            return result
        obj = json.loads(result)
        expire = obj.get("expire", -1)
        if expire < 0:
            return obj
        if expire < time.time():
            return None
        return obj.get("value")

    def put(self, key, value, expire = -1,  expire_random = 600):
        if expire > 0:
            expire = int(time.time() + expire)
            expire += random.randint(0, expire_random)
        obj = dict(key = key, value = value, expire = expire)
        return db_put(self.prefix + key, json.dumps(obj))

