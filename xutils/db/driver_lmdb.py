# -*- coding:utf-8 -*-
# @author mark
# @since 2022/03/20 14:43:04
# @modified 2022/03/20 23:31:24
# @filename driver_lmdb.py

import lmdb
import logging

class LmdbKV:

    def __init__(self, db_dir, debug = True, map_size = 1024**3):
        self.env = lmdb.open(db_dir, map_size = map_size)
        self.debug = debug

    def Get(self, key):
        """通过key读取Value
        @param {bytes} key
        @return {bytes|None} value
        """
        with self.env.begin() as tx:
            return tx.get(key)

    def Put(self, key, value, sync = False):
        """写入Key-Value键值对
        @param {bytes} key
        @param {bytes} value
        """
        if self.debug:
            logging.debug("Put: key(%s), value(%s)", key, value)

        with self.env.begin(write = True) as tx:
            tx.put(key, value)

    def Delete(self, key, sync = False):
        """删除Key-Value键值对
        @param {bytes} key
        """

        if self.debug:
            logging.debug("Delete: key(%s)", key)
        
        with self.env.begin(write = True) as tx:
            tx.delete(key)

    def RangeIter(self, 
            key_from = None, 
            key_to = None, 
            reverse = False,
            include_value = True, 
            fill_cache = False):
        """返回区间迭代器
        @param {bytes}  key_from       开始的key（包含）FirstKey
        @param {bytes}  key_to         结束的key（包含）LastKey
        @param {bool}   reverse        是否反向查询
        @param {bool}   include_value  是否包含值
        @param {bool}   fill_cache     是否填充缓存
        """
        if self.debug:
            logging.debug("RangeIter: key_from(%s), key_to(%s), reverse(%s)", 
                key_from, key_to, reverse)
        
        if reverse:
            for item in self.RangeIter_reverse(key_from, key_to, include_value):
                yield item
            return
            
        with self.env.begin() as tx:
            with tx.cursor() as cur:
                if key_from != None:
                    has_value = cur.set_range(key_from)
                else:
                    has_value = cur.first()
                
                if has_value:
                    if key_to != None and cur.key() > key_to:
                        return # 越界
                    if include_value:
                        yield cur.item()
                    else:
                        yield cur.key()

                while cur.next():
                    if key_to != None and cur.key() > key_to:
                        return # 越界
                    if include_value:
                        yield cur.item()
                    else:
                        yield cur.key()

    def RangeIter_reverse(self, key_from = None, key_to = None, 
            include_value = True):

        with self.env.begin() as tx:
            with tx.cursor() as cur:
                if key_to != None:
                    has_value = cur.set_range(key_to) # cur >= key_to
                    if not has_value: # 不存在>=key_to的值，移动到最后一位
                        has_value = cur.last()
                else:
                    has_value = cur.last() # 各种可能性

                if not has_value:
                    return

                if key_to != None and cur.key() > key_to: # cur > key_to 需要回溯1位
                    has_value = cur.prev()

                if not has_value:
                    return

                if key_from != None and cur.key() < key_from:
                    # 越界了
                    return

                if include_value:
                    yield cur.item()
                else:
                    yield cur.key()

                while cur.prev():
                    if key_from != None and cur.key() < key_from:
                        # 越界了
                        return
                    if include_value:
                        yield cur.item()
                    else:
                        yield cur.key()


    def CreateSnapshot(self):
        return self

    def Write(self, batch_proxy, sync = False):
        with self.env.begin(write = True) as tx:
            for key in batch_proxy._puts:
                value = batch_proxy._puts[key]
                tx.put(key, value)

            for key in batch_proxy._deletes:
                tx.delete(key)

    def Stat(self):
        return self.env.stat()

