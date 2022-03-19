# -*- coding:utf-8 -*-
# @author mark
# @since 2022/03/19 10:58:01
# @modified 2022/03/19 11:11:55
# @filename lock.py

import threading
import uuid
import time

class RecordLock:
    """行锁的实现"""

    _enter_lock = threading.RLock()
    _lock_dict  = dict()

    def __init__(self, lock_key):
        self.lock = None
        self.lock_key = lock_key
        self.token = uuid.uuid4().hex

    def acquire(self, timeout = -1):
        lock_key = self.lock_key

        wait_time_start = time.time()
        with RecordLock._enter_lock:
            while RecordLock._lock_dict.get(lock_key) != None:
                # 当前锁被占用，等待锁释放
                time.sleep(0.001)
                if timeout > 0:
                    wait_time = time.time() - wait_time_start
                    if wait_time > timeout:
                        return False
            # 由于_enter_lock已经加锁了，_lock_dict里面不需要再使用锁
            RecordLock._lock_dict[lock_key] = self.token
        return True

    def release(self):
        with RecordLock._enter_lock:
            cur_token = RecordLock._lock_dict[self.lock_key]
            if self.token == cur_token:
                del RecordLock._lock_dict[self.lock_key]
            else:
                logging.error("lock has been taken by other(%s)", cur_token)

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, type, value, traceback):
        self.release()

    def __del__(self):
        self.release()

