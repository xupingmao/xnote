# encoding=utf-8
###########################################################
# @desc db utilties
# @author xupingmao
# @email 578749341@qq.com
# @since 2015-11-02 20:09:44
# @modified 2022/04/16 09:26:49
###########################################################

"""xnote的数据库封装，基于键值对数据库（目前是基于leveldb，键值对功能比较简单，
方便在不同引擎之间切换）

由于KV数据库没有表的概念，dbutil基于KV模拟了表，基本结构如下
* <table_name>:[subkey1]:[subkey2]...[subkeyN]

编号  |      结构描述      | 示例
---- | ------------------|---------------------------
案例1 | <表名:用户名:主键>  | note:admin:0001
案例2 | <表名:标签:主键>    | note_public:tag1:0001
案例3 | <表名:属性名>       |  system_config:config1
案例4 | <表名:用户名:属性名> | user_config:user01:config1

注意：读写数据前要先调用register_table来注册表，不然会失败！

包含的方法如下
* get_table       获取一个表对象
* register_table  注册表，如果没注册系统会拒绝写入
* count_table     统计表记录数
* put
* get
* delete
* scan
* prefix_list
* prefix_iter
* prefix_count

"""
# 先加载标准库
from __future__ import print_function, with_statement
import re
import time
import threading
import logging

try:
    import sqlite3
except ImportError:
    # 部分运行时环境可能没有sqlite3
    sqlite3 = None

# 加载第三方的库
import xutils
from xutils.imports import is_str
from xutils import dateutil
from xutils.db.encode import convert_bytes_to_object, convert_object_to_json

try:
    import leveldb
except ImportError:
    # Windows环境没有leveldb，需要使用leveldbpy的代理实现
    leveldb = None

DEFAULT_BLOCK_CACHE_SIZE = 8 * (2 << 20)  # 16M
DEFAULT_WRITE_BUFFER_SIZE = 2 * (2 << 20)  # 4M
DEFAULT_CACHE_EXPIRE = 60 * 60  # 1小时

_write_lock = threading.RLock()
LAST_TIME_SEQ = -1

# 注册的数据库表名，如果不注册，无法进行写操作
TABLE_INFO_DICT = dict()
# 表的索引信息 dict[str] -> set[str]
INDEX_INFO_DICT = dict()

# leveldb表的缓存
LDB_TABLE_DICT = dict()

# 只读模式
WRITE_ONLY = False

# leveldb的全局实例
_leveldb = None
# 缓存对象（拥有put/get两个方法）
_cache = None

def print_debug_info(fmt, *args):
    new_args = [dateutil.format_time(), "[dbutil]"]
    new_args.append(fmt.format(*args))
    print(*new_args)


class DBException(Exception):
    pass


class WriteBatchProxy:
    """批量操作代理，批量操作必须在同步块中执行（必须加锁）"""

    def __init__(self):
        self._puts = {}
        self._deletes = set()

    def check_and_put(self, key, val):
        old_val = get(key)
        if old_val == val:
            # 值相同，不需要更新
            return
        self.put(key, val)

    def put(self, key, val):
        """put一个value
        @param {str} key
        @param {object} val
        """
        check_before_write(key)

        key_bytes = key.encode("utf-8")
        val_bytes = convert_object_to_json(val).encode("utf-8")

        self._deletes.discard(key_bytes)
        self._puts[key_bytes] = val_bytes

    def put_bytes(self, key, value):
        assert isinstance(key, bytes), key
        assert isinstance(value, bytes), value

        self._deletes.discard(key)
        self._puts[key] = value

    def check_and_delete(self, key):
        old_val = get(key)
        if old_val == None:
            # 值为空，不需要删除
            return
        self.delete(key)

    def delete(self, key):
        key_bytes = key.encode("utf-8")
        self._puts.pop(key_bytes, None)
        self._deletes.add(key_bytes)

    def log_debug_info(self):
        # 没有更新直接返回
        if len(self._puts) + len(self._deletes) == 0:
            return

        print_debug_info("----- batch.begin -----")
        for key in self._puts:
            value = self._puts[key]
            print_debug_info("batch.put key={}, value={}", key, value)
        for key in self._deletes:
            print_debug_info("batch.delete key={}", key)
        print_debug_info("-----  batch.end  -----")

    def commit(self, sync=False):
        self.log_debug_info()
        check_get_leveldb().Write(self, sync)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if traceback is None:
            self.commit()


def config(**kw):
    global WRITE_ONLY

    if "write_only" in kw:
        WRITE_ONLY = kw["write_only"]


def get_instance():
    if _leveldb is None:
        raise Exception("leveldb instance is None!")
    return _leveldb


def create_db_instance(db_dir, block_cache_size=None, write_buffer_size=None):
    if block_cache_size is None:
        block_cache_size = DEFAULT_BLOCK_CACHE_SIZE

    if write_buffer_size is None:
        write_buffer_size = DEFAULT_WRITE_BUFFER_SIZE

    logging.info("block_cache_size=%s", block_cache_size)

    if leveldb:
        return leveldb.LevelDB(db_dir,
                               block_cache_size=block_cache_size,
                               write_buffer_size=write_buffer_size)

    if xutils.is_windows():
        import leveldbpy
        return LevelDBProxy(db_dir,
                            block_cache_size=block_cache_size,
                            write_buffer_size=write_buffer_size)

    raise Exception("create_db_instance failed: not supported")


def check_not_empty(value, message):
    if value == None or value == "":
        raise Exception(message)


def get_write_lock(key=None):
    """获取全局独占的写锁，可重入"""
    global _write_lock
    return _write_lock


def timeseq(value=None):
    """生成一个时间序列
    @param {float|None} value 时间序列，单位是秒，可选
    @return {string}    20位的时间序列
    """
    global LAST_TIME_SEQ

    if value != None:
        error_msg = "expect <class 'float'> but see %r" % type(value)
        assert isinstance(value, float), error_msg

        value = int(value * 1000)
        return "%020d" % value

    t = int(time.time() * 1000)
    # 加锁防止并发生成一样的值
    # 注意这里的锁是单个进程级别的
    with get_write_lock():
        if t == LAST_TIME_SEQ:
            # 等于上次生成的值，说明太快了，sleep一下进行控速
            # print("too fast, sleep 0.001")
            # 如果不sleep，下次还可能会重复
            time.sleep(0.001)
            t = int(time.time() * 1000)
        LAST_TIME_SEQ = t
        return "%020d" % t


def new_id(prefix):
    return "%s:%s" % (prefix, timeseq())


def check_leveldb():
    if _leveldb is None:
        raise Exception("leveldb not found!")


def check_write_state():
    if WRITE_ONLY:
        raise Exception("write_only mode!")


def check_before_write(key):
    check_leveldb()
    check_write_state()
    check_not_empty(key, "[dbutil.put] key can not be None")

    table_name = key.split(":", 1)[0]
    check_table_name(table_name)


def check_get_leveldb():
    return get_instance()


def check_table_name(table_name):
    validate_str(table_name, "invalid table_name:{}", table_name)
    if table_name not in TABLE_INFO_DICT:
        raise DBException("table %r not registered!" % table_name)


def get_table_info(table_name):
    global TABLE_INFO_DICT
    return TABLE_INFO_DICT.get(table_name)


def validate_none(obj, msg, *argv):
    if obj != None:
        raise DBException(msg.format(*argv))


def validate_obj(obj, msg, *argv):
    if obj is None:
        raise DBException(msg.format(*argv))


def validate_str(obj, msg, *argv):
    if not is_str(obj):
        raise DBException(msg.format(*argv))


def validate_list(obj, msg, *argv):
    if not isinstance(obj, list):
        raise DBException(msg.format(*argv))


def validate_dict(obj, msg, *argv):
    if not isinstance(obj, dict):
        raise DBException(msg.format(*argv))


class TableInfo:

    def __init__(self, name, description, category):
        self.name = name
        self.description = description
        self.category = category
        self.check_user = False
        self.user_attr  = None


def register_table(table_name,
                   description,
                   category="default",
                   check_user=False):
    # TODO 考虑过这个方法直接返回一个 LdbTable 实例
    # LdbTable可能针对同一个`table`会有不同的实例
    if not re.match(r"^[0-9a-z_]+$", table_name):
        raise Exception("无效的表名:%r" % table_name)

    _register_table_inner(table_name, description, category, check_user)


def _register_table_inner(table_name,
                         description,
                         category="default",
                         check_user=False):
    if not re.match(r"^[0-9a-z_\$]+$", table_name):
        raise Exception("无效的表名:%r" % table_name)

    if table_name in TABLE_INFO_DICT:
        # 已经注册了
        return

    info = TableInfo(table_name, description, category)
    info.check_user = check_user

    TABLE_INFO_DICT[table_name] = info


def register_table_index(table_name, index_name):
    """注册表的索引"""
    validate_str(table_name, "invalid table_name")
    validate_str(index_name, "invalid index_name")
    check_table_name(table_name)
    index_info = INDEX_INFO_DICT.get(table_name)
    if index_info is None:
        index_info = set()
    index_info.add(index_name)
    INDEX_INFO_DICT[table_name] = index_info

    # 注册索引表
    index_table = get_index_table_name(table_name, index_name)
    description = "%s表索引" % table_name
    _register_table_inner(index_table, description)

def register_table_user_attr(table_name, user_attr):
    """注册表用户的属性名"""
    check_table_name(table_name)
    table_info = get_table_info(table_name)
    if table_info.user_attr != None:
        logging.warning("user_attr已经设置了")
    table_info.user_attr = user_attr

def get_table_dict_copy():
    return TABLE_INFO_DICT.copy()


def get_table_names():
    """获取表名称"""
    global TABLE_INFO_DICT
    values = sorted(TABLE_INFO_DICT.values(),
                    key=lambda x: (x.category, x.name))
    return list(map(lambda x: x.name, values))

def get_table_index_names(table_name):
    validate_str(table_name, "invalid table_name")
    return INDEX_INFO_DICT.get(table_name) or set()

def get_index_table_name(table_name, index_name):
    return "_index$%s$%s" % (table_name, index_name)

def get(*args, **kw):
    return db_get(*args, **kw)

def db_get(key, default_value=None):
    check_leveldb()
    try:
        if key == "" or key == None:
            return None

        key = key.encode("utf-8")
        value = _leveldb.Get(key)
        result = convert_bytes_to_object(value)
        if result is None:
            return default_value
        return result
    except KeyError:
        return default_value


def db_put(key, obj_value, sync=False):
    """往数据库中写入键值对
    @param {string} key 数据库主键
    @param {object} obj_value 值，会转换成JSON格式
    @param {boolean} sync 是否同步写入，默认为False
    """
    check_before_write(key)

    key = key.encode("utf-8")
    # 注意json序列化有个问题，会把dict中数字开头的key转成字符串
    value = convert_object_to_json(obj_value)
    # print("Put %s = %s" % (key, value))
    _leveldb.Put(key, value.encode("utf-8"), sync=sync)

def put(*args, **kw):
    return db_put(*args, **kw)

def put_bytes(key, value, sync=False):
    check_before_write(key.decode("utf-8"))
    _leveldb.Put(key, value, sync=sync)


def delete(key, sync=False):
    check_leveldb()
    check_write_state()

    print_debug_info("Delete {}", key)

    key = key.encode("utf-8")
    _leveldb.Delete(key, sync=sync)


def create_write_batch():
    return WriteBatchProxy()


def scan(key_from=None,
         key_to=None,
         func=None,
         reverse=False,
         parse_json=True):
    """扫描数据库
    @param {string|bytes} key_from
    @param {string|bytes} key_to
    @param {function} func
    @param {boolean} reverse
    """
    check_leveldb()

    if key_from != None and isinstance(key_from, str):
        key_from = key_from.encode("utf-8")

    if key_to != None and isinstance(key_to, str):
        key_to = key_to.encode("utf-8")

    iterator = _leveldb.RangeIter(key_from,
                                  key_to,
                                  include_value=True,
                                  reverse=reverse)

    for key, value in iterator:
        key = key.decode("utf-8")
        value = convert_bytes_to_object(value, parse_json)
        if not func(key, value):
            break


def prefix_scan(prefix, func, reverse=False, parse_json=True):
    check_leveldb()
    assert len(prefix) > 0

    key_from = None
    key_to = None

    if prefix[-1] != ':':
        prefix += ':'

    prefix_bytes = prefix.encode("utf-8")

    if reverse:
        # 反向查询
        key_from = prefix_bytes + b'\xff'
        key_to = prefix_bytes
    else:
        # 正向查询
        key_from = prefix_bytes
        key_to = None

    iterator = _leveldb.RangeIter(key_from,
                                  key_to,
                                  include_value=True,
                                  reverse=reverse,
                                  fill_cache=False)

    offset = 0
    for key, value in iterator:
        key = key.decode("utf-8")
        if not key.startswith(prefix):
            break
        value = convert_bytes_to_object(value, parse_json)
        if not func(key, value):
            break
        offset += 1


def prefix_list(*args, **kw):
    return list(prefix_iter(*args, **kw))


def prefix_iter(prefix,
                filter_func=None,
                offset=0,
                limit=-1,
                reverse=False,
                include_key=False,
                key_from=None,
                map_func=None,
                fill_cache=False):
    """通过前缀迭代查询
    @param {string} prefix 遍历前缀
    @param {function} filter_func 过滤函数
    @param {function} map_func 映射函数，如果返回不为空则认为匹配
    @param {int} offset 选择的开始下标，包含
    @param {int} limit  选择的数据行数
    @param {boolean} reverse 是否反向遍历
    @param {boolean} include_key 返回的数据是否包含key，默认只有value
    """
    check_leveldb()
    if key_from != None and reverse == True:
        raise Exception("不允许反向遍历时设置key_from")

    if filter_func != None and map_func != None:
        raise Exception("不允许同时设置filter_func和map_func")

    if prefix[-1] != ':':
        prefix += ':'

    origin_prefix = prefix
    prefix = prefix.encode("utf-8")

    if reverse:
        # 时序表的主键为 表名:用户名:时间序列 时间序列长度为20
        prefix += b'\xff'

    if key_from is None:
        key_from = prefix
    else:
        key_from = key_from.encode("utf-8")

    # print("prefix: %s, origin_prefix: %s, reverse: %s" %
    #      (prefix, origin_prefix, reverse))

    if reverse:
        key_from = None
        key_to = prefix
    else:
        key_to = None

    iterator = _leveldb.RangeIter(key_from,
                                  key_to,
                                  include_value=True,
                                  reverse=reverse,
                                  fill_cache=fill_cache)

    position = 0
    matched_offset = 0
    result_size = 0

    for key, value in iterator:
        key = key.decode("utf-8")
        if not key.startswith(origin_prefix):
            break
        value = convert_bytes_to_object(value)

        is_match = True

        if filter_func:
            is_match = filter_func(key, value)

        if map_func:
            value = map_func(key, value)
            is_match = value != None

        if is_match:
            if matched_offset >= offset:
                result_size += 1
                if include_key:
                    yield key, value
                else:
                    yield value
            matched_offset += 1

        if limit > 0 and result_size >= limit:
            break
        position += 1


def count(key_from=None, key_to=None, filter_func=None):
    check_leveldb()

    if key_from:
        key_from = key_from.encode("utf-8")
    if key_to:
        key_to = key_to.encode("utf-8")
    iterator = _leveldb.RangeIter(key_from, key_to, include_value=True)

    count = 0
    for key, value in iterator:
        key = key.decode("utf-8")
        value = convert_bytes_to_object(value)
        if filter_func(key, value):
            count += 1
    return count


def prefix_count(prefix,
                 filter_func=None,
                 offset=None,
                 limit=None,
                 reverse=None,
                 include_key=None,
                 map_func=None):
    """通过前缀统计行数
    @param {string} prefix 数据前缀
    @param {function} filter_func 过滤函数
    @param {object} offset  无意义参数，为了方便调用
    @param {object} limit   无意义参数，为了方便调用
    @param {object} reverse 无意义参数，为了方便调用
    @param {object} include_key 无意义参数，为了方便调用
    """
    if filter_func != None and map_func != None:
        raise Exception("不允许同时设置filter_func和map_func")

    count = [0]

    def func(key, value):
        if not key.startswith(prefix):
            return False
        if filter_func != None:
            if filter_func(key, value):
                count[0] += 1
            return True

        if map_func != None:
            if map_func(key, value) != None:
                count[0] += 1
            return True

        count[0] += 1
        return True

    prefix_scan(prefix, func)
    return count[0]

def set_db_cache(cache):
    global _cache
    _cache = cache

def set_db_instance(db_instance):
    global _leveldb
    _leveldb = db_instance

def count_table(table_name, use_cache=False):
    assert table_name != None
    assert table_name != ""

    if table_name[-1] != ":":
        table_name += ":"

    cache_key = "table_count:%s" % table_name

    if use_cache and _cache != None:
        value = _cache.get(cache_key)
        if value != None:
            logging.debug("count_table by cache, table_name:(%s), count:(%s)",
                          table_name, value)
            return value

    key_from = table_name.encode("utf-8")
    key_to = table_name.encode("utf-8") + b'\xff'
    iterator = check_get_leveldb().RangeIter(key_from,
                                             key_to,
                                             include_value=False,
                                             fill_cache=False)

    count = 0
    for key in iterator:
        count += 1

    if _cache != None:
        _cache.put(cache_key, count, expire=DEFAULT_CACHE_EXPIRE)
    return count


def count_all():
    """统计全部的KV数量"""
    iterator = check_get_leveldb().RangeIter(include_value=False,
                                             fill_cache=False)

    count = 0
    for key in iterator:
        count += 1
    return count


def _rename_table_no_lock(old_name, new_name):
    for key, value in prefix_iter(old_name, include_key=True):
        name, rest = key.split(":", 1)
        new_key = new_name + ":" + rest
        put(new_key, value)


def rename_table(old_name, new_name):
    with get_write_lock(old_name):
        with get_write_lock(new_name):
            _rename_table_no_lock(old_name, new_name)


def run_test():
    pass


if __name__ == "__main__":
    run_test()
