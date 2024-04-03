# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-04-03 22:58:18
@LastEditors  : xupingmao
@LastEditTime : 2024-04-04 01:01:19
@FilePath     : /xnote/xnote/service/lock_service.py
@Description  : 分布式锁服务
"""

import xutils
import time
import datetime

from xnote.core import xtables, xconfig

DEFAULT_LOCK_TIMEOUT_SECONDS = 60.0

def release_func(lock_key="", lock_token=""):
    pass

class LockObject:

    def __init__(self):
        self.lock_key = ""
        self.timeout_time = 0
        self.lock_token = ""
        self.got_lock = False
        self._release_func = release_func

    def release(self):
        if self.got_lock:
            self._release_func(self.lock_key, self.lock_token)
            self.got_lock = False

    def __enter__(self):
        if self.got_lock:
            return self
        raise Exception("acquire lock failed")

    def __exit__(self, type, value, traceback):
        self.release()

    def __del__(self):
        self.release()

class DatabaseLockService:
    """数据库锁服务"""

    db = xtables.get_table_by_name("t_lock")

    @classmethod
    def to_datetime(cls, value):
        if isinstance(value, str):
            return datetime.datetime.fromisoformat(value)
        if isinstance(value, datetime.datetime):
            return value
        raise Exception(f"unknown type {type(value)}")

    @classmethod
    def lock(cls, lock_key="", timeout_seconds=DEFAULT_LOCK_TIMEOUT_SECONDS):
        now_time = xutils.format_datetime()
        now_time_ms = time.time() * 1000
        timeout_time = int(now_time_ms + timeout_seconds* 1000)
        old_lock = cls.db.select_first(where=dict(lock_key=lock_key))
        
        if old_lock != None and old_lock.timeout_time < now_time_ms:
            # lock is timeout
            if xconfig.DatabaseConfig.db_driver_sql == "mysql":
                cls.db.delete(where="lock_key=$lock_key AND timeout_time < current_timestamp()*1000", 
                    vars=dict(lock_key=lock_key))
            else:
                cls.db.delete(where="lock_key=$lock_key AND timeout_time < $now_time_ms", 
                    vars=dict(lock_key=lock_key, now_time_ms=now_time_ms))
        
        if old_lock != None and old_lock.timeout_time >= now_time_ms:
            # lock is valid
            raise Exception(f"acquire lock failed, lock_key={lock_key}")
        
        lock_token = xutils.create_uuid()
        try:
            cls.db.insert(ctime=now_time, mtime=now_time, lock_key=lock_key, lock_token=lock_token, 
                          timeout_time=timeout_time)
        except:
            # create lock failed
            raise Exception(f"acquire lock failed, lock_key={lock_key}")
        
        lock = LockObject()
        lock.lock_key = lock_key
        lock.timeout_time = timeout_time
        lock.lock_token = lock_token
        lock._release_func = cls.release
        lock.got_lock = True
        return lock
    
    @classmethod
    def release(cls, lock_key="", lock_token=""):
        cls.db.delete(where=dict(lock_key=lock_key, lock_token=lock_token))
    
