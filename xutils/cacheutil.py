# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/06/07 22:10:11
# @modified 2022/04/04 13:42:52
"""持久化操作已经禁用，请使用dbutil
PS: 标准库 functools提供了缓存的方法， 参考 https://docs.python.org/zh-cn/3/library/functools.html


缓存的实现，API列表如下

* cache(key = None, prefix = None, expire = 600) 缓存装饰器，用于加速函数调用
* cache_put(key, value, expire = -1) 写入缓存
* cache_get(key, default_value = None) 读取缓存
* cache_del(key)  删除缓存

失效的检查策略
1. 读取时检查失效
2. 生成新的缓存时从队列中取出多个缓存进行检查

~~持久化策略~~
1. 初始化的时候从文件中读取，运行过程中直接从内存读取
2. 创建或者更新的时候持久化到文件
3. TODO 考虑持久化时的并发控制


淘汰置换规则（仅用于会失效的缓存）
1. FIFO, First In First Out
2. LRU, Least Recently Used
3. LFU, Least Frequently Used

* 参考redis的API
* TODO: 可以使用 BitCask 存储模型实现
"""
import threading
import random
import datetime
from xutils import dateutil
from collections import OrderedDict, deque
from xutils.imports import *
from xutils import interfaces
from xutils.db.dbutil_cache import DatabaseCache

_cache_dict = dict()
_cache_queue = deque()
STORAGE_DIR = None


def encode_key(text):
    """编码key为文件名"""
    return text + ".json"
    # return base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8") + ".pk"


def decode_key(text):
    """解码文件名称为key值，暂时没有使用"""
    return base64.urlsafe_b64decode(text[:-3].encode("utf-8")).decode("utf-8")


def format_key(key):
    """格式化key，先简单实现一版"""
    result = []
    for c in key:
        if c == "/":
            result.append("%47")
        elif c == "%":
            result.append("%25")
        elif c == ":":
            result.append("%58")
        else:
            result.append(c)
    return "".join(result)


def log_debug(msg):
    # print(msg)
    pass


def log_error(msg):
    print(msg)


class MemoryCache(interfaces.CacheInterface):
    """缓存实现,一般情况下不要直接用它,优先使用 PrefixedCache, 这样便于迁移到Redis之类的分布式缓存"""

    def __init__(self, max_size = -1):
        self.dict = OrderedDict()
        self.expire_dict = dict()
        self.max_size = max_size
        self.lock = threading.RLock()

    def _fix_storage(self, obj):
        if isinstance(obj, dict):
            return Storage(**obj)
        if isinstance(obj, list):
            for index, item in enumerate(obj):
                if isinstance(item, dict):
                    obj[index] = Storage(**item)
            return obj
        return obj

    def get(self, key, default_value=None):
        assert isinstance(key, str), key
        value = self.dict.get(key)
        if value != None:
            if self.is_alive(key):
                self.dict[key] = value # 移到最后面
                if isinstance(value, bytes):
                    obj = value
                else:
                    obj = json.loads(value)
                return self._fix_storage(obj)
            else:
                self.delete(key)
        return default_value
    
    def get_raw(self, key):
        return self.dict.get(key)
    
    def format_value(self, value):
        if isinstance(value, dict):
            result = dict()
            for key in value:
                item_value = value.get(key)
                if isinstance(item_value, datetime.datetime):
                    result[key] = dateutil.format_datetime(item_value)
                else:
                    result[key] = item_value
            return result
        return value

    def put(self, key, value, expire=60*5, random_range=60*5):
        assert expire > 0
        with self.lock:
            if isinstance(value, bytes):
                self.dict[key] = value
            else:
                value = self.format_value(value)
                self.dict[key] = json.dumps(value) # 转成json，要保证能够序列化
            self.expire_dict[key] = time.time() + expire + random.randint(0, random_range)
            
            if self.max_size > 0:
                self.check_size_and_clear()

    def is_alive(self, key):
        value = self.expire_dict.get(key, 60*5)
        return value > time.time()
    
    def delete(self, key):
        has_delete = False
        with self.lock:
            if key in self.dict:
                del self.dict[key]
                has_delete = True
            if key in self.expire_dict:
                del self.expire_dict[key]
                has_delete = True
        return has_delete

    def check_size_and_clear(self):
        if self.max_size <= 0:
            return

        while len(self.dict) > self.max_size:
            key, value = self.dict.popitem(last=False) # 弹出第一个
            self.delete(key)
    
    def get_expire(self, key):
        return self.expire_dict.get(key)

    def keys(self):
        return list(self.dict.keys())
    
    def clear_expired(self):
        """清理失效的缓存"""
        for key in self.keys():
            if not self.is_alive(key):
                self.delete(key)

class DummyCache:
    """用于禁用缓存, 兼容缓存的API"""

    def __init__(self, max_size=-1):
        pass

    def get(self, key):
        return None
    
    def put(self, key, value, expire=-1):
        pass

    def delete(self, key):
        pass

class Cache(MemoryCache):
    pass

_global_cache = MemoryCache(max_size=1000)

class PrefixedCache:

    def __init__(self, prefix="", cache_engine=interfaces.empty_cache):
        self.prefix = prefix
        if cache_engine == interfaces.empty_cache:
            self.cache = _global_cache
        else:
            self.cache = cache_engine
    
    def get(self, key, default_value=None):
        return self.cache.get(self.prefix + key, default_value=default_value)
    
    def get_dict(self, key, default_value=None):
        value = self.cache.get(self.prefix + key, default_value=default_value)
        if value == None:
            return None
        assert isinstance(value, dict)
        return value
    
    def put(self, key, value, expire=60*5):
        return self.cache.put(self.prefix+key, value, expire)
    
    def put_empty(self, key, expire=5):
        """针对空值的特殊处理"""
        return self.cache.put(self.prefix+key, "$empty", expire)
    
    def is_empty(self, value):
        return value == "$empty"
    
    def delete(self, key):
        return self.cache.delete(self.prefix + key)

def get_global_cache():
    return _global_cache


class MultiLevelCache(interfaces.CacheInterface):
    """基于内存+数据库的多级缓存"""

    def __init__(self):
        self.database_cache = DatabaseCache()
        self.mem_cache = _global_cache
        self.mem_cache_expire = 60

    def get(self, key, default_value=None):
        # 先查内存缓存
        value = self.mem_cache.get(key)
        if value == None:
            # 如果查不到，查数据库缓存
            value = self.database_cache.get(key)
            if value != None:
                self.mem_cache.put(key, value)
        if value == None:
            return default_value
        return value
    
    def put(self, key, value, expire = -1, expire_random = 600):
        self.database_cache.put(key, value, expire=expire, expire_random=expire_random)
        self.mem_cache.put(key, value, expire=self.mem_cache_expire)
    
    def delete(self, key):
        self.database_cache.delete(key)
        self.mem_cache.delete(key)

class CacheObj:
    """缓存对象，包含缓存的key和value，有一个公共的缓存队列
    每次生成一个会从缓存队列中取出一个检查是否失效，同时把自己放入队列
    TODO 提供按照大小过滤的规则
    """
    # 缓存的最大容量，用于集合类型
    max_size = -1
    valid_key_pattern = re.compile(r"^[0-9a-zA-Z\[\]_\-\.\(\)\@\#,'\"\$ ]+$")

    def __init__(self, key, value, expire=-1, type="object", need_save=True):
        global _cache_dict
        global _cache_queue

        self.check_key_value(key, value)

        self.key = key
        self.value = value
        self.expire = expire
        self.expire_time = time.time() + expire
        self.type = type
        self.is_force_expired = False

        if type == "zset" and not isinstance(value, OrderedDict):
            value = OrderedDict(**value)
            self.value = value

        if expire < 0:
            self.expire_time = -1

        obj = _cache_dict.get(key, None)
        if obj is not None:
            obj.is_force_expired = True

        if need_save:
            self.save()

        _cache_queue.append(self)

        # find and clear expired cache objects
        try:
            for i in range(3):
                if len(_cache_queue) == 0:
                    break
                one = _cache_queue.popleft()
                if one is not None:
                    if one.is_force_expired == True:
                        continue
                    if one.is_alive():
                        _cache_queue.append(one)
                    else:
                        one.clear()
        except:
            # queue.Empty异常
            print_exc()

    def check_key_value(self, key, value):
        if key is None:
            raise ValueError("key cannot be None")
        if value is None:
            raise ValueError("invalid key: value is None")
        if len(key) > 200:
            raise ValueError("invalid key: len(key)>200")

    def is_valid_key(self, key):
        return self.valid_key_pattern.match(key) != None

    def _get_path(self, key):
        assert STORAGE_DIR != None
        return os.path.join(STORAGE_DIR, key + ".json")

    def get_dump_value(self):
        if self.type == "zset":
            return dict(**self.value)
        else:
            return self.value

    def save(self, method_name="save"):
        _cache_dict[self.key] = self
        if self.is_temp():
            return

        # save to disk
        raise Exception(
            "cacheutil.%s to disk is no longer supprted, please use dbutil" % method_name)


    def is_alive(self):
        if self.is_force_expired:
            return False
        if self.expire_time < 0:
            return True
        return time.time() < self.expire_time

    def is_temp(self):
        return self.expire_time > 0

    def get_value(self):
        if self.is_alive():
            return self.value
        self.clear()
        return None

    def clear(self):
        log_debug("clear cache %s" % self.key)
        # 标记为删除，用于清除queue中的引用
        self.is_force_expired = True
        _cache_dict.pop(self.key, None)
        if self.is_temp():
            return
        # remove from disk
        path = self._get_path(self.key)
        if os.path.exists(path):
            os.remove(path)


def cache_deco(key=None, prefix=None, expire=600, expire_random=600):
    """缓存的装饰器，会自动清理失效的缓存
    注意：不考虑持久化，如果有持久化需要使用db实现
    @param {str} key    指定缓存的key，也就是使用固定的key
    @param {str} prefix 指定缓存的前缀，使用前缀+函数参数的方式，也就是动态的key
    如果 key 和prefix 都不指定，使用函数签名+函数参数的方式，生成动态的key
    """
    if key != None and prefix != None:
        raise Exception("不能同时设置key和prefix参数")

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

            cache_value = _global_cache.get(key=cache_key)
            if cache_value is not None:
                return cache_value
            value = func(*args)
            if value is None:
                _global_cache.delete(key=cache_key)
                return None

            _global_cache.put(key=cache_key, value=value, expire=expire, random_range=expire_random)
            return value
        return handle
    return deco


def cache_call(cache_key, func, expire=600, expire_random=600):
    """带缓存的函数调用,这种方式可以生成可读性更高的cache_key"""
    assert isinstance(cache_key, str)
    cache_value = _global_cache.get(key=cache_key)
    if cache_value is not None:
        return cache_value
    value = func()
    if value is None:
        _global_cache.delete(key=cache_key)
        return None

    _global_cache.put(key=cache_key, value=value, expire=expire, random_range=expire_random)
    return value

def kw_cache_deco(prefix="", expire=600, expire_random=600):
    """缓存的装饰器，会自动清理失效的缓存
    注意：不考虑持久化，如果有持久化需要使用db实现
    @param {str} key    指定缓存的key，也就是使用固定的key
    @param {str} prefix 指定缓存的前缀，使用前缀+函数参数的方式，也就是动态的key
    如果 key 和prefix 都不指定，使用函数签名+函数参数的方式，生成动态的key
    """
    assert prefix != ""

    def deco(func):
        # 先不支持keywords参数
        def handle(*args, **kw):
            cache_key = "%s(%s_%s)" % (prefix, args, kw)
            cache_value = _global_cache.get(key=cache_key)
            if cache_value is not None:
                return cache_value
            value = func(*args, **kw)
            if value is None:
                _global_cache.delete(key=cache_key)
                return None

            _global_cache.put(key=cache_key, value=value, expire=expire, random_range=expire_random)
            return value
        return handle
    return deco


def cache(*args, **kw):
    return cache_deco(*args, **kw)


def put(key, value=None, expire=-1):
    """设置缓存的值
    @param {object} value value对象必须可以json序列化，如果value为None，会删除key对应的对象
    @param {integer} expire 失效时间，单位秒，如果小于等于0认为不失效，会持久化到文件
    """
    return _global_cache.put(key, value=value, expire=expire)


def get(key, default_value=None):
    """读取缓存对象
    @param {object} default_value 如果缓存对象不存在，返回default_value
    """
    return _global_cache.get(key=key, default_value=default_value)


def delete(key=None, prefix=None, args=None):
    """使key对应的缓存失效，成功返回True
    del与python关键字冲突
    @param {string} key 缓存的key
    """
    if key == None:
        key = "%s%s" % (prefix, args)
    return _global_cache.delete(key=key)


def prefix_del(prefix):
    """使用前缀删除"""
    for key in _global_cache.dict:
        if key.startswith(prefix):
            _global_cache.delete(key)


# 方法别名
cache_get = get
cache_put = put
cache_del = delete
set = put


def get_cache_obj(key, default_value=None, type=None):
    if not is_str(key):
        raise TypeError("cache key must be string")
    obj = _cache_dict.get(key)
    if obj is None:
        return default_value
    if obj.is_alive():
        if type != None and type != obj.type:
            raise TypeError("expect %s but found %s" % (type, obj.type))
        return obj
    obj.clear()
    return None


def update_cache_by_key(key):
    """直接通过key来更新缓存，前提是缓存已经存在"""
    obj = _cache_dict.get(key)
    if obj != None:
        func = obj.func
        args = obj.args
        obj.value = func(*args)


def lpush(key, value):
    obj = get_cache_obj(key, type="list")
    if obj != None and obj.value != None:
        obj.value.insert(0, value)
        obj.save()
    else:
        obj = CacheObj(key, [value], type="list")
        obj.save()


def rpush(key, value):
    obj = get_cache_obj(key, type="list")
    if obj != None and obj.value != None:
        obj.value.append(value)
        obj.save()
    else:
        obj = CacheObj(key, [value], type="list")
        obj.save()


def lrange(key, start=0, stop=-1):
    obj = get_cache_obj(key, type="list")
    if obj != None and obj.value != None:
        length = len(obj.value)
        if start < 0:
            start += length
        if stop < 0:
            stop += length
        return obj.value[start: stop+1]
    else:
        return []


def ltrim(key, start=0, stop=-1):
    obj = get_cache_obj(key, type="list")
    if obj != None and obj.value != None:
        length = len(obj.value)
        if start < 0:
            start += length
        if stop < 0:
            stop += length
        obj.value = obj.value[start: stop+1]
        obj.save()
    else:
        pass


def lindex(key, index):
    obj = get_cache_obj(key, type="list")
    if obj != None and obj.value != None:
        length = len(obj.value)
        if index < 0:
            index += length
        if index >= length or index < 0:
            return None
        return obj.value[index]
    else:
        return None


class SortedObject:

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __lt__(self, obj):
        return self.value < obj.value

    def __cmp__(self, obj):
        return cmp(self.value, obj.value)


def zadd(key, score, member):
    # TODO 双写两个列表
    obj = get_cache_obj(key, type="zset")
    if obj != None and obj.value != None:
        obj.value.pop(member, None)
        obj.value[member] = score
        obj.type = "zset"
        obj.save()
    else:
        obj = CacheObj(key, OrderedDict(), type="zset")
        obj.value[member] = score
        obj.save()


def zrange(key, start, stop):
    """zset分片，不同于Python，这里是左右包含，包含start，包含stop
    :arg int start: 从0开始，负数表示倒数
    :arg int stop: 从0开始，负数表示倒数
    TODO 优化排序算法，使用有序列表+哈希表
    """
    obj = get_cache_obj(key)
    if obj != None:
        items = obj.value.items()
        if stop == -1:
            stop = len(items)
        else:
            stop += 1
        sorted_items = sorted(items, key=lambda x: x[1])
        sorted_keys = [k[0] for k in sorted_items]
        return sorted_keys[start: stop]
    return []


def zcount(key):
    obj = get_cache_obj(key)
    if obj != None:
        return len(obj.value)
    return 0


def zscore(key, member):
    obj = get_cache_obj(key)
    if obj != None:
        return obj.value.get(member, None)
    return None


def zincrby(key, increment, member):
    """通过setdefault处理并发问题"""
    obj = get_cache_obj(key)
    if obj != None:
        obj.value.setdefault(member, 0)
        obj.value[member] += increment
        # obj.value.move_to_end(member, last=True)
        obj.value[member] = obj.value.pop(member)
        if obj.max_size > 0:
            # LRU置换
            while len(obj.value) > obj.max_size:
                obj.value.popitem(last=False)
        obj.save()
    else:
        zadd(key, increment, member)


def zrem(key, member):
    obj = get_cache_obj(key)
    if obj != None:
        value = obj.value.pop(member)
        if value != None:
            obj.save()
            return 1
        return 0
    else:
        return 0


def zremrangebyrank(key, start, stop):
    '''删除zset区间'''
    obj = get_cache_obj(key)
    if obj is None:
        return 0
    members = zrange(key, start, stop)
    if len(members) == 0:
        return 0
    for member in members:
        log_debug("del %s" % member)
        obj.value.pop(member)
    obj.save()
    return len(members)


def zmaxsize(key, max_size):
    obj = get_cache_obj(key)
    if obj is None:
        return
    obj.max_size = max_size


def hset(key, field, value, expire=-1):
    try:
        obj = get_cache_obj(key, type="hash")
        if obj != None and obj.value != None:
            obj.value[field] = value
            obj.type = "hash"
            obj.save("hset")
        else:
            obj = CacheObj(key, dict(), type="hash", expire=expire)
            obj.value[field] = value
            obj.save("hset")
    except:
        print_exc()
        return None


def hget(key, field):
    try:
        obj = get_cache_obj(key, type="hash")
        if obj != None and obj.value != None:
            return obj.value.get(field)
        else:
            return None
    except:
        print_exc()
        return None


def hdel(key, field):
    obj = get_cache_obj(key, type="hash")
    if obj != None and obj.value != None:
        if field in obj.value:
            del obj.value[field]
            return 1
        return 0
    else:
        return 0


def hkeys(key, field):
    obj = get_cache_obj(key, type="hash")
    if obj != None and obj.value != None:
        return list(obj.value.keys())
    else:
        return list()


def keys(pattern=None):
    """返回所有缓存的key列表"""
    return list(_cache_dict.keys())


def print_exc():
    """打印系统异常堆栈"""
    ex_type, ex, tb = sys.exc_info()
    exc_info = traceback.format_exc()
    log_error(exc_info)


def json_object_hook(dict_obj):
    return Storage(**dict_obj)


def load_dump():
    dirname = STORAGE_DIR
    valid_ext_tuple = (".json")
    for fname in os.listdir(dirname):
        if not fname.endswith(valid_ext_tuple):
            continue
        try:
            fpath = os.path.join(dirname, fname)
            with open(fpath, "rb") as fp:
                pickled = fp.read()
                if pickled == b'':
                    continue
                if fname.endswith(".json"):
                    dict_obj = json.loads(pickled.decode(
                        "utf-8"), object_hook=json_object_hook)
                else:
                    dict_obj = pickle.loads(pickled)
                # 持久化的都是不失效的数据
                obj_type = dict_obj.get("type", "object")
                obj = CacheObj(
                    dict_obj["key"], dict_obj["value"], -1, type=obj_type, need_save=False)
                if obj.is_temp():
                    os.remove(fpath)
        except:
            log_error("failed to load cache %s" % fname)
            print_exc()


def clear_temp():
    for key in _cache_dict.copy():
        value = _cache_dict.get(key)
        if value != None and value.is_temp():
            value.clear()


def init(storage_dir):
    global STORAGE_DIR
    STORAGE_DIR = storage_dir
