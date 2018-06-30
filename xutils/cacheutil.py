# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/06/07 22:10:11
# @modified 2018/06/30 15:39:15
"""
缓存的实现，考虑失效的规则如下
1. 按时间失效
2. FIFO, First In First Out
3. LRU, Least Recently Used
4. LFU, Least Frequently Used
"""
from .imports import *
_cache_dict = dict()

class CacheObj:
    """
    缓存对象，包含缓存的key和value，有一个公共的缓存队列
    每次生成一个会从缓存队列中取出一个检查是否失效，同时把自己放入队列
    TODO 提供按照大小过滤的规则
    """
    _queue = Queue()

    def __init__(self, key, value, expire):
        global _cache_dict
        self.key = key
        self.value = value
        self.expire = expire
        self.expire_time = time.time() + expire
        self.is_force_expired = False

        if expire < 0:
            self.expire_time = -1

        obj = _cache_dict.get(key, None)
        if obj is not None:
            obj.is_force_expired = True

        _cache_dict[key] = self
        self._queue.put(self)
        one = self._queue.get(block=False)
        if one is not None:
            if one.is_force_expired == True:
                return
            if one.is_alive():
                self._queue.put(one)
            else:
                one.clear()

    def is_alive(self):
        if self.expire_time < 0:
            return True
        return time.time() < self.expire_time

    def clear(self):
        # print("cache %s expired" % self.key)
        _cache_dict.pop(self.key, None)

def cache(key=None, prefix=None, expire=600):
    """
    缓存的装饰器，会自动清理失效的缓存
    TODO 可以考虑缓存持久化的问题
    """
    def deco(func):
        # 先不支持keywords参数
        def handle(*args):
            if key is not None:
                cache_key = key
            elif prefix is None:
                mod = inspect.getmodule(func)
                funcname = func.__name__
                cache_key = "%s.%s%s" % (mod.__name__, funcname, args)
            else:
                cache_key = "%s%s" % (prefix, args)
            obj = _cache_dict.get(cache_key)
            if obj != None and obj.is_alive():
                # print("hit cache %s" % cache_key)
                return obj.value
            if obj != None and not obj.is_alive():
                obj.clear()
            value = func(*args)
            cache_obj = CacheObj(cache_key, value, expire)
            cache_obj.func = func
            cache_obj.args = args
            return value
        return handle
    return deco


def expire_cache(key = None, prefix = None, args = None):
    """使key对应的缓存失效，成功返回True"""
    if key == None:
        key = "%s%s" % (prefix, args)
    obj = _cache_dict.get(key)
    if obj != None:
        # 防止删除了新的cache
        obj.clear()
        obj.is_force_expired = True
        return True
    return False

def put_cache(key = None, value = None, prefix = None, args = None, expire = -1):
    """设置缓存的值"""
    if key is None:
        key = '%s%s' % (prefix, args)
    _cache_dict[key] = CacheObj(key, value, expire)

def get_cache(key):
    """获取缓存的值"""
    obj = _cache_dict.get(key)
    if obj is None:
        return None
    return obj.value

update_cache = put_cache

def update_cache_by_key(key):
    """
    直接通过key来更新缓存，前提是缓存已经存在
    """
    obj = _cache_dict.get(key)
    if obj != None:
        func = obj.func
        args = obj.args
        obj.value = func(*args)
