# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-01-25 22:37:52
@LastEditors  : xupingmao
@LastEditTime : 2023-06-22 10:15:34
@FilePath     : /xnote/xutils/db/dbutil_deque.py
@Description  : 基于Key-Value数据库的双端队列
"""

import threading
from xutils import Storage
from xutils.db.dbutil_base import create_write_batch, db_get, db_put
from xutils.db.encode import encode_index_value


class MetaInfo(Storage):
    """双端队列的元信息"""

    def __init__(self) -> None:
        self._id = ""
        self._key = ""
        self.first_id = 0
        self.last_id = 0
        self.size = 0


class DequeTable:

    _lock = threading.RLock()

    def __init__(self, table_name, max_size=2 ** 63):
        self.max_size = max_size
        self.table_name = table_name
        self.meta_key = "_meta:" + self.table_name

    def get_meta_info(self):
        info = db_get(self.meta_key)
        if info == None:
            return MetaInfo()
        else:
            assert isinstance(info, dict)
            result = MetaInfo()
            result.update(info)
            return result

    def update_meta_info(self, info):
        db_put(self.meta_key, info)

    def __len__(self):
        return self.get_meta_info().size

    def build_key(self, id):
        return self.table_name + ":" + encode_index_value(id)

    def get_by_id(self, id):
        key = self.build_key(id)
        return db_get(key)

    def append(self, value, batch=None):
        with self._lock:
            meta = self.get_meta_info()
            last_id = meta.last_id

            if meta.size >= self.max_size:
                raise Exception("deque max size excceeded (%d)" % meta.size)

            if meta.size == 0:
                meta.first_id = 1
                meta.last_id = 1
                next_id = 1
            else:
                next_id = last_id + 1
                if next_id >= self.max_size:
                    next_id = next_id % self.max_size

            key = self.build_key(next_id)

            meta.last_id = next_id
            meta.size += 1

            if batch:
                batch.put(key, value)
                batch.put(self.meta_key, meta)
            else:
                batch = create_write_batch()
                batch.put(key, value)
                batch.put(self.meta_key, meta)
                batch.commit()

    def appendleft(self, value, batch=None):
        with self._lock:
            meta = self.get_meta_info()
            first_id = meta.first_id

            if meta.size >= self.max_size:
                raise Exception("deque max size excceeded (%d)" % meta.size)

            if meta.size == 0:
                meta.first_id = 1
                meta.last_id = 1
                prev_id = 1
            else:
                prev_id = first_id - 1
                if prev_id < 0:
                    prev_id += self.max_size

            key = self.build_key(prev_id)

            meta.first_id = prev_id
            meta.size += 1

            if batch:
                batch.put(key, value)
                batch.put(self.meta_key, meta)
            else:
                batch = create_write_batch()
                batch.put(key, value)
                batch.put(self.meta_key, meta)
                batch.commit()

    def popleft(self):
        with self._lock:
            meta = self.get_meta_info()
            if meta.size == 0:
                raise Exception("deque is empty")

            first_id = meta.first_id
            first_value = self.get_by_id(first_id)
            first_id += 1
            if first_id >= self.max_size:
                first_id = first_id % self.max_size

            meta.first_id = first_id
            meta.size -= 1

            self.update_meta_info(meta)
            return first_value

    def pop(self):
        with self._lock:
            meta = self.get_meta_info()
            if meta.size == 0:
                raise Exception("deque is empty")

            last_id = meta.last_id
            last_value = self.get_by_id(last_id)
            last_id -= 1
            if last_id < 0:
                last_id += self.max_size

            meta.last_id = last_id
            meta.size -= 1

            self.update_meta_info(meta)
            return last_value

    def first(self):
        with self._lock:
            meta = self.get_meta_info()
            if meta.size == 0:
                raise Exception("deque is empty")
            return self.get_by_id(meta.first_id)

    def last(self):
        with self._lock:
            meta = self.get_meta_info()
            if meta.size == 0:
                raise Exception("deque is empty")
            return self.get_by_id(meta.last_id)
