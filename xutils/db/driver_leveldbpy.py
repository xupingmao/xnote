# -*- coding:utf-8 -*-
# @author mark
# @since 2022/03/19 10:03:49
# @modified 2022/03/20 21:30:05
# @filename driver_leveldbpy.py

import leveldbpy
from xutils import interfaces

class LevelDBProxy(interfaces.DBInterface):

    def __init__(self, path=None, snapshot=None,
                 max_open_files=1000,
                 block_cache_size=8 * (2 << 20),
                 write_buffer_size=2 * (2 << 20),
                 config_dict=None):
        """通过leveldbpy来实现leveldb的接口代理，因为leveldb没有提供Windows环境的支持"""
        self.config_dict = None
        if snapshot != None:
            self._db = snapshot
        else:
            assert path != None
            self._db = leveldbpy.DB(
                path.encode("utf-8"),
                create_if_missing=True,
                block_cache_size=block_cache_size,
                max_open_files=max_open_files,
                write_buffer_size=write_buffer_size)

    def Get(self, key):
        return self._db.get(key)

    def Put(self, key, value, sync=False):
        return self._db.put(key, value, sync=sync)

    def Delete(self, key, sync=False):
        return self._db.delete(key, sync=sync)

    def RangeIter_reverse(self, iterator, key_from=None, key_to=None):
        iterator.seek(key_to)     # cur >= key_to
        if not iterator.valid():  # 如果没有匹配的，移动到尾部
            iterator.seekLast()

        def try_seek_prev():
            try:
                return iterator.prev()
            except StopIteration:
                return None

        # 反向遍历有三种情况:
        # 1. 没有命中key并且后面也没有任何值，需要往前移动
        # 2. 找到key后面的一个值，需要往前移动
        # 3. 刚好命中key，不需要处理

        if not iterator.valid():
            # 一个匹配的都没有，直接返回
            return

        if iterator.key() > key_to:
            # cur > key_to: 需要 seek prev
            try_seek_prev()

        while True:
            try:
                if not iterator.valid():
                    return

                if iterator.key() < key_from:
                    return

                if iterator._keys_only:
                    yield iterator.key()
                else:
                    yield (iterator.key(), iterator.value())

                iterator.prev()
            except StopIteration:
                return

    def RangeIter(self,
                  key_from=None,
                  key_to=None,
                  reverse=False,
                  include_value=True,
                  fill_cache=False):
        """返回区间迭代器
        :param {bytes}  key_from: 开始的key（包含）
        :param {bytes}  key_to: 结束的key（包含）
        :param {bool} reverse: 是否反向查询
        :param {bool} include_value: 是否包含值
        """
        # assert key_from <= key_to
        if include_value:
            keys_only = False
        else:
            keys_only = True

        if key_from == None:
            key_from = b''

        if key_to == None:
            key_to = b'\xff'

        iterator = self._db.iterator(keys_only=keys_only)

        if reverse:
            for item in self.RangeIter_reverse(iterator, key_from, key_to):
                yield item
            return

        iterator.seek(key_from)

        while True:
            if not iterator.valid():
                # raise StopIteration()
                return
            key = iterator.key()
            # print(key, key_to)
            if key > key_to:
                # raise StopIteration()
                return

            if include_value:
                yield iterator.key(), iterator.value()
            else:
                yield iterator.key()

            try:
                iterator.next()
            except StopIteration:
                return

    def CreateSnapshot(self):
        return LevelDBProxy(snapshot=self._db.snapshot())

    def Write(self, batch_proxy, sync=False):
        """执行批量操作"""
        assert isinstance(batch_proxy, interfaces.BatchInterface)
        batch = leveldbpy.WriteBatch()
        for key in batch_proxy._puts:
            value = batch_proxy._puts[key]
            batch.put(key, value)
        for key in batch_proxy._inserts:
            value = batch_proxy._inserts[key]
            old_value = self.Get(key)
            if old_value != None:
                raise interfaces.new_duplicate_key_exception(key)
            batch.put(key, value)
        for key in batch_proxy._deletes:
            batch.delete(key)
        return self._db.write(batch, sync)
