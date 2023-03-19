# -*- coding:utf-8 -*-
# @author mark
# @since 2022/03/19 10:58:01
# @modified 2022/03/19 11:11:55
# @filename lock.py

import threading
import uuid
import time
import logging


class RecordLock:
    """行锁的实现
    TODO 基于数据库的持久化锁
    TODO 后台进程为锁续期
    """

    _enter_lock = threading.RLock()
    _lock_dict = dict()

    def __init__(self, lock_key, expire=-1):
        self.lock = None
        self.lock_key = lock_key
        self.token = uuid.uuid4().hex
        self.expire = expire
        self.got_lock_time = None

    def is_expired(self):
        if self.expire < 0:
            return False

        assert self.got_lock_time != None
        return (time.time() - self.got_lock_time) > self.expire

    def acquire(self, timeout=-1):
        lock_key = self.lock_key

        wait_time_start = time.time()
        while True:
            with self._enter_lock:
                lock = self._lock_dict.get(lock_key)
                if lock == self:
                    return True
                if lock == None or lock.is_expired():
                    self._lock_dict[lock_key] = self
                    self.got_lock_time = time.time()
                    return True
                    
                # print("lock required by ({lock_key}, {token}, {expire}) self.token:{self_token}".format(
                #     lock_key=lock_key, token=lock.token, expire=lock.expire, self_token=self.token))

            # 当前锁被占用，释放_enter_lock，等待后重新尝试获取锁
            time.sleep(0.001)
            if timeout > 0:
                wait_time = time.time() - wait_time_start
                if wait_time > timeout:
                    return False

    def release(self):
        with self._enter_lock:
            lock = self._lock_dict.get(self.lock_key)
            if lock == None:
                return
            if self == lock:
                del self._lock_dict[self.lock_key]
            else:
                logging.error("lock has been taken by other(%s)", lock.token)

    def __enter__(self):
        lock = self.acquire()
        if lock:
            return self
        raise Exception("get lock failed")

    def __exit__(self, type, value, traceback):
        self.release()

    def __del__(self):
        self.release()
    
    @classmethod
    def clear_expired(cls):
        with cls._enter_lock:
            for key in cls._lock_dict.keys():
                lock = cls._lock_dict.get(key)
                if lock != None and lock.is_expired():
                    del cls._lock_dict[key]
