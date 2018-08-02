# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/06/07 22:10:11
# @modified 2018/08/03 02:12:15
"""
缓存的实现，考虑失效的规则如下

失效的检查策略
1. 读取时检查失效
2. 生成新的缓存时从队列中取出多个缓存进行检查

持久化策略
1. 初始化的时候从文件中读取，运行过程中直接从内存读取
2. 创建或者更新的时候持久化到文件
3. TODO 考虑持久化时的并发控制


淘汰置换规则（仅用于会失效的缓存）
1. FIFO, First In First Out
2. LRU, Least Recently Used
3. LFU, Least Frequently Used

参考redis的API
"""
from .imports import *
_cache_dict = dict()

def encode_key(text):
    """编码key为文件名"""
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8") + ".pk"

def decode_key(text):
    """解码文件名称为key值，暂时没有使用"""
    return base64.urlsafe_b64decode(text[:-3].encode("utf-8")).decode("utf-8")


class CacheObj:
    """
    缓存对象，包含缓存的key和value，有一个公共的缓存队列
    每次生成一个会从缓存队列中取出一个检查是否失效，同时把自己放入队列
    TODO 提供按照大小过滤的规则
    """
    _queue = Queue()

    def __init__(self, key, value, expire=-1):
        global _cache_dict
        
        if value is None:
            print("invalid key [%s], value is None" % key)
            return

        self.key              = key
        self.value            = value
        self.expire           = expire
        self.expire_time      = time.time() + expire
        self.type             = "object"
        self.is_force_expired = False

        if expire < 0:
            self.expire_time = -1

        obj = _cache_dict.get(key, None)
        if obj is not None:
            obj.is_force_expired = True

        self.save()
        self._queue.put(self)

        one = self._queue.get(block=False)
        if one is not None:
            if one.is_force_expired == True:
                return
            if one.is_alive():
                self._queue.put(one)
            else:
                one.clear()

    def _get_path(self, key):
        return os.path.join(xconfig.STORAGE_DIR, encode_key(key))

    def save(self):
        _cache_dict[self.key] = self
        # save to disk
        path = self._get_path(self.key)
        obj = dict(key = self.key, 
                type = self.type,
                value = self.value, 
                expire_time = self.expire_time)
        pickled = pickle.dumps(obj)
        with open(path, "wb") as fp:
            fp.write(pickled)

    def is_alive(self):
        if self.is_force_expired:
            return False
        if self.expire_time < 0:
            return True
        return time.time() < self.expire_time

    def get_value(self):
        if self.is_alive():
            return self.value
        self.clear()
        return None

    def clear(self):
        # print("cache %s expired" % self.key)
        _cache_dict.pop(self.key, None)
        # remove from disk
        path = self._get_path(self.key)
        if os.path.exists(path):
            os.remove(path)

def cache(key=None, prefix=None, expire=600):
    """
    缓存的装饰器，会自动清理失效的缓存ge
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

def get(key, default_value=None):
    """获取缓存的值"""
    obj = _cache_dict.get(key)
    if obj is None:
        return default_value
    return obj.get_value()

get_cache = get

def get_cache_obj(key, default_value=None):
    obj = _cache_dict.get(key)
    obj = _cache_dict.get(key)
    if obj is None:
        return default_value
    if obj.is_alive():
        return obj
    obj.clear()
    return None

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

class SortedObject:

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __lt__(self, obj):
        return self.value < obj.value

    def __cmp__(self, obj):
        return cmp(self.value, obj.value)

def zadd(key, score, member):
    obj = get_cache_obj(key)
    if obj != None and obj.value != None:
        if obj.type != "zset":
            raise TypeError("require zset but found %s" % obj.type)
        obj.value[member] = score
        obj.type = "zset"
        obj.save()
    else:
        obj = CacheObj(key, dict())
        obj.value[member] = score
        obj.type = "zset"
        obj.save()

def zrange(key, start, stop):
    """zset分片，包含start、stop"""
    obj = get_cache_obj(key)
    if obj != None:
        items = obj.value.items()
        if stop == -1:
            stop = len(items)
        else:
            stop += 1
        sorted_items = sorted(items, key = lambda x: x[1])
        sorted_keys = [k[0] for k in sorted_items]
        return sorted_keys[start: stop]
    return []

def zcount(key):
    obj = get_cache_obj(key)
    if obj != None:
        return len(obj.value)
    return 0

def keys(pattern=None):
    return _cache_dict.keys()

def set(key, value, expire=-1):
    CacheObj(key, value, expire)

def delete(key):
    """del与python关键字冲突"""
    obj = get_cache_obj(key)
    if obj != None:
        obj.clear()

def print_exc():
    """打印系统异常堆栈"""
    ex_type, ex, tb = sys.exc_info()
    exc_info = traceback.format_exc()
    print(exc_info)

def load_dump():
    dirname = xconfig.STORAGE_DIR
    for fname in os.listdir(dirname):
        if not fname.endswith(".pk"):
            continue
        try:
            fpath = os.path.join(dirname, fname)
            with open(fpath, "rb") as fp:
                pickled = fp.read()
                dict_obj = pickle.loads(pickled)
                obj = CacheObj(dict_obj["key"], 
                    dict_obj["value"], 
                    dict_obj["expire_time"] - time.time())
                obj.type = dict_obj.get("type", "object")
        except:
            print_exc()

