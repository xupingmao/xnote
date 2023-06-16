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
案例3 | <表名:属性名>       | system_config:config1
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
import logging

try:
    import sqlite3
except ImportError:
    # 部分运行时环境可能没有sqlite3 比如Jython
    sqlite3 = None

# 加载第三方的库
import xutils
from xutils.imports import is_str
from xutils import dateutil
from xutils.db.encode import convert_bytes_to_object, convert_object_to_json
from .driver_interface import DBInterface, BatchInterface
from .dbutil_id_gen import TimeSeqId
from . import driver_interface

try:
    import leveldb
except ImportError:
    # Windows环境没有leveldb，需要使用leveldbpy的代理实现
    leveldb = None

DEFAULT_BLOCK_CACHE_SIZE = 8 * (2 << 20)  # 16M
DEFAULT_WRITE_BUFFER_SIZE = 2 * (2 << 20)  # 4M
DEFAULT_CACHE_EXPIRE = 60 * 60 * 24  # 1天

# 注册的数据库表名，如果不注册，无法进行写操作
TABLE_INFO_DICT = dict()
# 表的索引信息 dict[str] -> set[str]
INDEX_INFO_DICT = dict()

# leveldb表的缓存
LDB_TABLE_DICT = dict()

# 只读模式
READ_ONLY = False

# leveldb的全局实例
_leveldb = driver_interface.empty_db

# 缓存对象（拥有put/get两个方法）
_cache = driver_interface.empty_cache
_driver_name = ""

get_write_lock = driver_interface.get_write_lock

def print_debug_info(fmt, *args):
    new_args = [dateutil.format_time(), "[dbutil]"]
    new_args.append(fmt.format(*args))
    print(*new_args)


class DBException(Exception):

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class WriteBatchProxy(BatchInterface):
    """批量操作代理，批量操作必须在同步块中执行（必须加锁）"""

    def __init__(self, db_instance=None):
        self._puts = {}
        self._deletes = set()
        if db_instance == None:
            db_instance = get_instance()

        self.db_instance = db_instance  # type: DBInterface
        self.debug = False

    def check_and_put(self, key, val):
        old_val = get(key)
        if old_val == val:
            # 值相同，不需要更新
            return
        self.put(key, val)

    def put(self, key, val, check_table=True):
        # type: (str, object, bool) -> None
        """put一个value
        @param {str} key
        @param {object} val
        """
        check_before_write(key, check_table)

        key_bytes = key.encode("utf-8")
        val_bytes = convert_object_to_json(val).encode("utf-8")

        self._deletes.discard(key_bytes)
        self._puts[key_bytes] = val_bytes

    def put_bytes(self, key, value):
        # type: (bytes, bytes) -> None
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
        # type: (str) -> None
        key_bytes = key.encode("utf-8")
        self._puts.pop(key_bytes, None)
        self._deletes.add(key_bytes)

    def size(self):
        return len(self._puts) + len(self._deletes)
    
    def _print_log(self, fmt="", *args):
        if self.debug:
            new_args = [dateutil.format_time(), "[dbutil]"]
            new_args.append(fmt.format(*args))
            print(*new_args)

    def log_debug_info(self):
        # 没有更新直接返回
        if self.size() == 0:
            return

        self._print_log("----- batch.begin -----")
        for key in self._puts:
            value = self._puts[key]
            self._print_log("batch.put key={}, value={}", key, value)
        for key in self._deletes:
            self._print_log("batch.delete key={}", key)
        self._print_log("-----  batch.end  -----")

    def commit(self, sync=False, retries=0):
        self.log_debug_info()
        while retries >= 0:
            try:
                self.db_instance.Write(self, sync)
                return
            except:
                xutils.print_exc()
                time.sleep(0.2)
                retries -= 1

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if traceback is None:
            self.commit()


def config(**kw):
    global READ_ONLY

    if "read_only" in kw:
        READ_ONLY = kw["read_only"]


def get_instance():
    if _leveldb is None:
        raise Exception("leveldb instance is None!")
    return _leveldb

def check_not_empty(value, message):
    if value == None or value == "":
        raise Exception(message)


def timeseq(value=None):
    """生成一个时间序列
    @param {float|None} value 时间序列，单位是秒，可选
    @return {string}    20位的时间序列
    """
    return TimeSeqId.create(value)


def new_id(prefix):
    return "%s:%s" % (prefix, timeseq())


def check_leveldb():
    if _leveldb is None:
        raise Exception("leveldb not found!")


def check_write_state():
    if READ_ONLY:
        raise Exception("read_only mode!")


def check_before_write(key, check_table=True):
    check_leveldb()
    check_write_state()
    check_not_empty(key, "[dbutil.put] key can not be None")

    if check_table:
        table_name = key.split(":", 1)[0]
        check_table_name(table_name)


def check_get_leveldb():
    return get_instance()


def check_table_name(table_name):
    validate_str(table_name, "invalid table_name:{}", table_name)
    if not TableInfo.is_registered(table_name):
        raise DBException("table %r not registered!" % table_name)


def get_table_info(table_name):
    return TableInfo.get_by_name(table_name)


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
    """表信息管理"""

    _info_dict = dict() # type: dict[str, TableInfo]

    def __init__(self, name, description, category):
        self.name = name
        self.description = description
        self.category = category
        self.check_user = False
        self.user_attr = None
        self.is_deleted = False

    @classmethod
    def register(cls, name, description, category):
        if name in cls._info_dict:
            return cls._info_dict[name]
        table = TableInfo(name, description, category)
        cls._info_dict[name] = table
        return table

    @classmethod
    def is_registered(cls, name):
        return name in cls._info_dict

    @classmethod
    def get_by_name(cls, name):
        # type: (str) -> TableInfo | None
        return cls._info_dict.get(name)

    @classmethod
    def get_dict_copy(cls):
        return cls._info_dict.copy()

    @classmethod
    def get_table_names(cls):
        values = sorted(cls._info_dict.values(),
                        key=lambda x: (x.category, x.name))
        return list(map(lambda x: x.name, values))

    def get_index_names(self):
        return IndexInfo.get_table_index_names(self.name)

    def register_index(self, index_name, *, columns = [], comment="", index_type="ref"):
        register_table_index(self.name, index_name, columns = columns,
                             comment = comment, index_type=index_type)
        return self

    def drop_index(self, index_name, comment = ""):
        # TODO 记录删除的索引
        return self

    def rebuild_index(self, version="v1"):
        from . import dbutil_table
        db = dbutil_table.LdbTable(self.name)
        db.rebuild_index(version)
    
    def delete_table(self):
        self.is_deleted = True

class IndexInfo:

    _table_dict = dict()  # type: dict[str, dict[str, IndexInfo]]

    def __init__(self, table_name, index_name, index_type="ref"):
        self.table_name = table_name
        self.index_name = index_name
        self.index_type = index_type
        self.columns = [index_name]
        self.ignore_none_value = True # 忽略None值

    @classmethod
    def register(cls, table_name, index_name, columns, index_type):
        info = IndexInfo(table_name, index_name, index_type)
        info.columns = columns
        index_dict = cls._table_dict.get(table_name)
        if index_dict == None:
            index_dict = dict()
        index_dict[index_name] = info
        cls._table_dict[table_name] = index_dict

    @classmethod
    def get_table_index_names(cls, table_name):
        index_dict = cls._table_dict.get(table_name)
        if index_dict == None:
            return set()
        return index_dict.keys()

    @classmethod
    def get_table_index_info(cls, table_name, index_name):
        index_dict = cls._table_dict.get(table_name)
        if index_dict == None:
            return None
        return index_dict.get(index_name)

    @classmethod
    def get_table_index_dict(cls, table_name):
        return cls._table_dict.get(table_name)

    @staticmethod
    def build_prefix(table_name, index_name):
        return "%s$%s" % (table_name, index_name)


def register_table(table_name,
                   description,
                   *,
                   category="default",
                   check_user=False,
                   user_attr=None):  # type: (...)->TableInfo
    # TODO 考虑过这个方法直接返回一个 LdbTable 实例
    # LdbTable可能针对同一个`table`会有不同的实例
    if not re.match(r"^[0-9a-z_]+$", table_name):
        raise Exception("无效的表名:%r" % table_name)

    return _register_table_inner(table_name, description,
                                 category, check_user, user_attr)


def _register_table_inner(table_name,
                          description,
                          category="default",
                          check_user=False,
                          user_attr=None):
    if not re.match(r"^[0-9a-z_\$]+$", table_name):
        raise Exception("无效的表名:%r" % table_name)
    
    if user_attr != None:
        check_user = True

    old_table = TableInfo.get_by_name(table_name)
    if old_table != None:
        # 检查结构是否一致，不能注册不一致的结构
        assert old_table.check_user == check_user, "conflict table registry: %s" % table_name
        assert old_table.user_attr == user_attr, "confilct table registry: %s" % table_name
        # 已经注册
        return old_table

    info = TableInfo.register(table_name, description, category)
    info.check_user = check_user
    info.user_attr = user_attr

    return info


def register_table_index(table_name, index_name, columns = [], comment="", index_type="ref"):
    """注册表的索引"""
    validate_str(table_name, "invalid table_name")
    validate_str(index_name, "invalid index_name")
    if index_type not in ("ref", "copy"):
        raise Exception("invalid index_type:(%s)" % index_type)

    check_table_name(table_name)

    if len(columns) == 0:
        columns = [index_name]

    IndexInfo.register(table_name, index_name, columns, index_type)

    # 注册索引表
    index_table = get_index_table_name(table_name, index_name)
    description = "%s表索引" % table_name
    _register_table_inner(index_table, description)


def register_table_user_attr(table_name, user_attr):
    """注册表用户的属性名"""
    check_table_name(table_name)
    table_info = get_table_info(table_name)
    assert table_info != None
    if table_info.user_attr != None:
        logging.warning("user_attr已经设置了")
    table_info.user_attr = user_attr
    table_info.check_user = True


def get_table_dict_copy():
    return TableInfo.get_dict_copy()


def get_table_names():
    """获取表名称"""
    return TableInfo.get_table_names()


def get_table_index_names(table_name):
    return IndexInfo.get_table_index_names(table_name)


def get_index_table_name(table_name, index_name):
    return IndexInfo.build_prefix(table_name, index_name)


def get(*args, **kw):
    return db_get(*args, **kw)


def db_get(key, default_value=None):
    check_leveldb()
    try:
        if key == "" or key == None:
            return None
        
        if not isinstance(key, str):
            # print("key=%r", key)
            raise TypeError("expect str but see %r" % type(key))

        key = key.encode("utf-8")
        value = _leveldb.Get(key)
        result = convert_bytes_to_object(value)
        if result is None:
            return default_value
        return result
    except KeyError:
        return default_value

def db_batch_get(key_list, default_value=None):
    # type: (list[str], object) -> dict[str, object]
    """批量查询"""
    check_leveldb()
    
    key_bytes_list = []
    for key in key_list:
        key_bytes_list.append(key.encode("utf-8"))

    batch_result = _leveldb.BatchGet(key_bytes_list)
    result = dict()
    for key in batch_result:
        value = batch_result.get(key)
        object = convert_bytes_to_object(value)
        if object is None:
            object = default_value
        result[key.decode("utf-8")] = object
    return result


def db_put(key, obj_value, sync=False, check_table=True):
    """往数据库中写入键值对
    @param {string} key 数据库主键
    @param {object} obj_value 值，会转换成JSON格式
    @param {boolean} sync 是否同步写入，默认为False
    """
    check_before_write(key, check_table)

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


def db_delete(key, sync=False):
    check_leveldb()
    check_write_state()

    # 删除日志
    print_debug_info("Delete {}", key)

    key = key.encode("utf-8")
    _leveldb.Delete(key, sync=sync)


def delete(*args, **kw):
    return db_delete(*args, **kw)


def create_write_batch(db_instance=None):
    return WriteBatchProxy(db_instance=db_instance)


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
    assert isinstance(key_from, (str, bytes))
    assert isinstance(key_to, (str, bytes))

    if isinstance(key_from, str):
        key_from = key_from.encode("utf-8")

    if isinstance(key_to, str):
        key_to = key_to.encode("utf-8")

    iterator = _leveldb.RangeIter(
        key_from, key_to,
        include_value=True, reverse=reverse)

    for key, value in iterator:
        key = key.decode("utf-8")
        value = convert_bytes_to_object(value, parse_json)
        if not func(key, value):
            break


def prefix_list(*args, **kw):
    return list(prefix_iter(*args, **kw))


def prefix_iter(prefix,  # type: str
                filter_func=None,  # type: function|None
                offset=0,  # type: int
                limit=-1,  # type: int
                reverse=False,
                include_key=False,
                *,
                key_from=None, key_to=None, map_func=None,
                fill_cache=False, parse_json=True, scan_db=False):
    """通过前缀迭代查询
    @param {string} prefix 遍历前缀
    @param {function} filter_func(str, object) 过滤函数
    @param {function} map_func(str, object)    映射函数，如果返回不为空则认为匹配
    @param {int} offset 选择的开始下标，包含
    @param {int} limit  选择的数据行数
    @param {boolean} reverse 是否反向遍历
    @param {boolean} include_key 返回的数据是否包含key，默认只有value
    @param {boolean} scan_db 是否扫描整个数据库
    @param {string} key_from 开始的key
    """
    check_leveldb()

    if filter_func != None and map_func != None:
        raise Exception("不允许同时设置filter_func和map_func")

    if scan_db == False:
        assert len(prefix) > 0, "prefix不能为空"
        if prefix[-1] != ':':
            prefix += ':'

    prefix_bytes = prefix.encode("utf-8")
    if key_from == None:
        key_from_bytes = prefix_bytes
    else:
        key_from_bytes = key_from.encode("utf-8")

    if key_to == None:
        key_to_bytes = prefix_bytes + b'\xff'
    else:
        key_to_bytes = key_to.encode("utf-8")

    iterator = _leveldb.RangeIter(
        key_from_bytes, key_to_bytes, include_value=True,
        reverse=reverse, fill_cache=fill_cache)

    position = 0
    matched_offset = 0
    result_size = 0

    if parse_json:
        convert_value_func = convert_bytes_to_object
    else:
        def convert_value_func(x): return x.decode("utf-8")

    for key_bytes, value in iterator:
        if not key_bytes.startswith(prefix_bytes):
            break
        key = key_bytes.decode("utf-8")
        value = convert_value_func(value)

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
    else:
        key_from = b''

    if key_to:
        key_to = key_to.encode("utf-8")
    else:
        key_to = b'0xff'
        
    iterator = _leveldb.RangeIter(key_from, key_to, include_value=True)

    count = 0
    for key, value in iterator:
        key = key.decode("utf-8")
        value = convert_bytes_to_object(value)
        if filter_func(key, value):
            count += 1
    return count


def prefix_count(*args, **kw):
    """通过前缀统计行数
    @param {string} prefix 数据前缀
    @param {function} filter_func 过滤函数
    @param {object} offset  无意义参数，为了方便调用
    @param {object} limit   无意义参数，为了方便调用
    @param {object} reverse 无意义参数，为了方便调用
    @param {object} include_key 无意义参数，为了方便调用
    """
    count = 0
    kw["include_key"] = False
    for value in prefix_iter(*args, **kw):
        count += 1
    return count


def set_db_cache(cache):
    global _cache
    _cache = cache


def set_db_instance(db_instance):
    global _leveldb
    _leveldb = db_instance


def get_db_instance():
    global _leveldb
    return _leveldb

def delete_table_count_cache(table_name):
    if _cache == None:
        return

    cache_key = "table_count:%s" % table_name
    _cache.delete(cache_key)

def delete_index_count_cache(table_name, index_name):
    if _cache == None:
        return

    index_prefix = IndexInfo.build_prefix(table_name, index_name)
    cache_key = "table_count:%s" % index_prefix
    _cache.delete(cache_key)


def count_table(table_name, use_cache=False):
    assert table_name != None
    assert table_name != ""

    cache_key = "table_count:%s" % table_name

    if table_name[-1] != ":":
        table_name += ":"

    if use_cache and _cache != None:
        value = _cache.get(cache_key)
        if value != None:
            logging.debug("count_table by cache, table_name:(%s), count:(%s)",
                          table_name, value)
            return value

    key_from = table_name.encode("utf-8")
    key_to = table_name.encode("utf-8") + b'\xff'
    count = _leveldb.Count(key_from, key_to)
    if _cache != None:
        _cache.put(cache_key, count, expire=DEFAULT_CACHE_EXPIRE)
    return count


def count_all():
    """统计全部的KV数量"""
    iterator = check_get_leveldb().RangeIter(
        include_value=False, fill_cache=False)

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


def set_driver_name(driver_name):
    global _driver_name
    _driver_name = driver_name


def get_driver_name():
    return _driver_name


if __name__ == "__main__":
    run_test()
