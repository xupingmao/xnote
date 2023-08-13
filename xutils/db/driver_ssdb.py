# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-07-29 19:49:39
@LastEditors  : xupingmao
@LastEditTime : 2023-08-06 11:35:34
@FilePath     : /xnote/xutils/db/driver_ssdb.py
@Description  : ssdb驱动,可以看成是leveldb的server版本
"""

import logging

from xutils import interfaces

class SSDBKV(interfaces.DBInterface):

    log_debug = False

    def __init__(self, **kw):
        """ssdb代理"""
        host = kw.get("host", "127.0.0.1")
        port = kw.get("port", 8888)
        import pyssdb
        self.db = pyssdb.Client(host=host, port=port)
        self.driver_type = "ssdb"

    def list_to_dict(self, list_result):
        dict_result = {}
        key = b''
        count = 0
        for item in list_result:
            count += 1
            if count % 2 == 1:
                key = item
            if count % 2 == 0:
                value = item
                dict_result[key] = value
        return dict_result

    def Get(self, key):
        return self.db.get(key)

    def Put(self, key, value, sync = False):
        return self.db.set(key, value)

    def Delete(self, key, sync = False):
        return self.db.delete(key)
    
    def BatchGet(self, keys=[]):
        if len(keys) == 0:
            return dict()
        result = self.db.multi_get(*keys)
        return self.list_to_dict(result)
    
    def BatchPut(self, kv_dict={}):
        kv_list = []
        for key in kv_dict:
            value = kv_dict.get(key)
            kv_list.append(key)
            kv_list.append(value)
        self.db.multi_set(*kv_list)

    def RangeIter(self, 
                  key_from = b'', # type: bytes
                  key_to = b'',  # type: bytes
                  reverse = False,
                  include_value = True, 
                  **kw):
        if self.log_debug:
            logging.info("RangeIter(args=%s, kw=%s)", (key_from,key_to,reverse), kw)
        
        if reverse:
            return self.RangeIterRaw(key_to,key_from, reverse, include_value)
        else:
            return self.RangeIterRaw(key_from, key_to, reverse, include_value)


    def RangeIterRaw(self, 
                  key1 = b'', # type: bytes
                  key2 = b'',  # type: bytes
                  reverse=False,
                  include_value = True, 
                  limit=100,
                  **kw):
        
        if include_value:
            value = self.db.get(key1)
            if value != None:
                yield key1, value

            prev_key = key1
            while True:
                count = 0
                if reverse:
                    data = self.db.rscan(prev_key, key2, limit)
                else:
                    data = self.db.scan(prev_key, key2, limit)

                if len(data) == 0:
                    return
                for item in data:
                    count+=1
                    if count%2==0:
                        value = item
                        yield prev_key, value
                    if count%2==1:
                        prev_key = item
        else:
            if self.db.exists(key1) == b'1':
                yield key1

            prev_key = key1
            while True:
                if reverse:
                    data = self.db.rkeys(prev_key, key2, limit)
                else:
                    data = self.db.keys(prev_key, key2, limit)
                if len(data) == 0:
                    return
                for item in data:
                    prev_key = item
                    yield item


    def CreateSnapshot(self):
        raise Exception("CreateSnapshot not supported")

    def Write(self, batch_proxy, sync = False):
        """执行批量操作"""
        return super().Write(batch_proxy)

    def Increase(self, key=b'', increment=1, start_id=1):
        result_int = self.db.incr(key, increment)
        if result_int < start_id:
            diff = start_id - result_int
            result_int = self.db.incr(key, diff)
        return result_int