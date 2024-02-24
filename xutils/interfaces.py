# -*- coding:utf-8 -*-
# @author mark
# @since 2022/03/19 23:28:08
# @modified 2022/03/20 14:42:16
# @filename driver_interface.py

"""这里定义一个通用的K-V数据库接口
PS: 接口是以Leveldb的接口为模板定义的
"""
import web
import warnings
import threading

_write_lock = threading.RLock()

def get_write_lock(key=""):
    # type: (str) -> threading.RLock
    """获取全局独占的写锁，可重入"""
    global _write_lock
    return _write_lock


class DatabaseException(Exception):

    def __init__(self, code=0, message=""):
        self.code = code
        super().__init__(message)


def new_duplicate_key_exception(key=b''):
    return Exception("Duplicate key: %s" % key)

class DBInterface:
    """KV存储的数据库接口"""

    def __init__(self, *args, **kw):
        self.driver_type = ""
        self.debug = False
        self.log_debug = False

    def Get(self, key):
        # type: (bytes) -> bytes
        """通过key读取Value
        @param {bytes} key
        @return {bytes|None} value
        """
        raise NotImplementedError("Get")
    
    def BatchGet(self, keys=[]):
        """批量get操作"""
        result = dict()
        for key in keys:
            result[key] = self.Get(key)
        return result

    def Put(self, key, value, sync = False):
        # type: (bytes,bytes,bool) -> None
        """写入Key-Value键值对
        @param {bytes} key
        @param {bytes} value
        """
        raise NotImplementedError("Put")

    def BatchPut(self, kv_dict={}):
        for key in kv_dict:
            value = kv_dict.get(key)
            self.Put(key, value)

    def Insert(self, key=b'', value=b'', sync=False):
        key_str = key.decode("utf-8")
        with get_write_lock(key_str):
            old = self.Get(key)
            if old == None:
                self.Put(key, value, sync=sync)
            else:
                raise new_duplicate_key_exception(key)


    def Delete(self, key, sync = False):
        # type: (bytes, bool) -> None
        """删除Key-Value键值对
        @param {bytes} key
        """
        raise NotImplementedError("Delete")
    
    def BatchDelete(self, keys=[]):
        for key in keys:
            self.Delete(key)
    
    def RangeIter(self, 
            key_from = b'', # type: bytes
            key_to = b'',  # type: bytes
            reverse = False,
            include_value = True, 
            fill_cache = False):
        """返回区间迭代器
        @param {bytes}  key_from       开始的key（包含）FirstKey 字节顺序小的key
        @param {bytes}  key_to         结束的key（包含）LastKey  字节顺序大的key
        @param {bool}   reverse        是否反向查询
        @param {bool}   include_value  是否包含值
        @param {bool}   fill_cache     是否填充缓存
        """
        assert key_from <= key_to
        if include_value:
            yield b'test-key', b'test-value'
        else:
            yield b'test-key'

    def CreateSnapshot(self):
        raise NotImplementedError("CreateSnapshot")

    def Write(self, batch_proxy, sync = False):
        """兜底的批量操作,不保证原子性"""
        assert isinstance(batch_proxy, BatchInterface)
        
        if len(batch_proxy._puts) > 0:
            self.BatchPut(batch_proxy._puts)
        
        for key in batch_proxy._inserts:
            value = batch_proxy._inserts[key]
            self.Insert(key, value)

        if len(batch_proxy._deletes) > 0:
            self.BatchDelete(batch_proxy._deletes)

    def Count(self, key_from:bytes, key_to:bytes):
        iterator = self.RangeIter(
            key_from, key_to, include_value=False, fill_cache=False)
        count = 0
        for key in iterator:
            count += 1
        return count
    
    def Increase(self, key=b'', increment=1, start_id=1):
        """自增方法"""
        assert len(key) > 0, "key can not be empty"
        
        key_str = key.decode("utf-8")
        with get_write_lock(key_str):
            value = self.Get(key)
            if value == None:
                value_int = start_id
            else:
                value_int = int(value)
                value_int += increment

            value_bytes = str(value_int).encode("utf-8")
            self.Put(key, value_bytes)
            return value_int


class DBLockInterface:
    """基于数据库的锁的接口"""

    def Acquire(self, resource_id, timeout):
        """返回token
        @return {str} token
        """
        raise NotImplementedError("Acquire")
    
    def Release(self, resource_id, token):
        raise NotImplementedError("Release")
    
    def Refresh(self, resource_id, token, refresh_time):
        raise NotImplementedError("Refresh")

class RecordInterface:
    """数据库记录的接口
    一般情况下推荐继承 xutils.Storage
    继承自Storage无法调用类的方法, 这种情况下可以继承当前的接口
    """

    def from_dict(self, dict_value: dict):
        """从数据库记录转为领域模型"""
        self.__dict__.update(dict_value)

    def to_dict(self):
        """从领域模型转为数据库记录"""
        return self.__dict__

class BatchInterface:
    """批量操作"""

    def __init__(self):
        self._deletes = set()
        self._puts = {}
        self._inserts = {}

    def check_and_delete(self, key: str):
        raise NotImplementedError("待子类实现")
    
    def check_and_put(self, key:str, value):
        raise NotImplementedError("待子类实现")

    def commit(self, sync=False, retries=0):
        raise NotImplementedError("待子类实现")


class CacheInterface:
    """缓存接口"""

    def get(self, key, default_value=None):
        return None
    
    def put(self, key, value, expire = -1, expire_random = 600):
        return None
    
    def delete(self, key):
        warnings.warn("CacheInterface.delete is not implemented")

class SqlLoggerInterface:

    def append(self, sql):
        pass

class ProfileLog(web.Storage):

    def __init__(self):
        self.type = ""
        self.ctime = ""
        self.cost_time = 0.0
        self.table_name = ""
        self.op_type = ""

class ProfileLogger:
    
    def log(self, log):
        pass


class SortedSetInterface:
    """有序集合接口, 参考redis的sortedset结构, 但是score限制在int范围"""

    def put(self, member="", score=0):
        pass

    def get(self, member=""):
        return 0
    
    def delete(self, member=""):
        pass
    
    def list_by_score(self, **kw):
        return []
    
class SQLDBInterface:
    table_name = ""
    
    def insert(self, seqname=None, _test=False, **values):
        return 0

    def select(self, vars=None, what='*', where=None, order=None, group=None,
               limit=None, offset=None, _test=False):
        return []
    
    def select_first(self, vars=None, what='*', where=None, order=None, group=None,
               limit=None, offset=None, _test=False):
        return None
    
    def update(self, where, vars=None, _test=False, **values):
        pass

    def delete(self,  where, using=None, vars=None, _test=False):
        pass

    def get_column_names(self):
        return []
    
    def count(self, where=None, sql=None, vars=None):
        return 0

empty_db = DBInterface()
empty_cache = CacheInterface()
