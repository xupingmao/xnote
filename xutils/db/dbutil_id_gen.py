# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-10-03 22:51:40
@LastEditors  : xupingmao
@LastEditTime : 2023-09-23 11:59:05
@FilePath     : /xnote/xutils/db/dbutil_id_gen.py
@Description  : id生成
"""
import time
import struct
import xutils
from xutils.db import dbutil_base as base
from xutils.db.encode import encode_id

class IdGenerator:

    def __init__(self, table_name) -> None:
        self.table_name = table_name

    def create_increment_id(self, start_id=1):
        new_id = self.create_increment_id_int(start_id=start_id)
        return encode_id(new_id)
    
    def create_increment_id_int(self, start_id=1, increment=1):
        assert start_id > 0
        max_id_key = "_max_id:" + self.table_name
        key_bytes = max_id_key.encode("utf-8")
        return base.get_db_instance().Increase(key_bytes, start_id=start_id, increment=increment)
    
    def current_id_int(self):
        max_id_key = "_max_id:" + self.table_name
        key_bytes = max_id_key.encode("utf-8")
        value = base.get_db_instance().Get(key_bytes)
        if value == None:
            return 0
        return int(value)

    def create_new_id(self, id_type="uuid", id_value=None):
        if id_type == "uuid":
            base.validate_none(id_value, "invalid id_value")
            return xutils.create_uuid()

        if id_type == "timeseq":
            base.validate_none(id_value, "invalid id_value")
            return TimeSeqId.create(id_value)

        if id_type == "auto_increment":
            base.validate_none(id_value, "invalid id_value")
            return self.create_increment_id()

        if id_type == "value":
            assert id_value != None
            return id_value

        raise Exception("unknown id_type:%s" % id_type)



class TimeSeqId:

    """时间序列ID生成器,第1位数字用于标识ID版本,不保证定长"""

    last_time_seq = (time.time() * 1000)
    max_retry = 100

    @classmethod
    def create(cls, value):
        """生成一个时间序列, python目前支持的最大时间是 9999 年
        @param {float|None} value 时间序列，单位是秒，可选
        @return {string}    16位字符串
        """
        return cls.create_v1(value)

    @classmethod
    def get_valid_ms(cls, value):
        if value != None:
            error_msg = "expect <class 'float'> but see %r" % type(value)
            assert isinstance(value, float), error_msg

            return int(value * 1000)
        else:
            t = int(time.time() * 1000)
            # 加锁防止并发生成一样的值
            # 注意这里的锁是单个进程级别的,后续可以考虑分布式锁,在时间戳后面增加机器的编号用于防止重复
            with base.get_write_lock("time_seq"):
                for retry in range(cls.max_retry):
                    if t <= cls.last_time_seq:
                        # 等于上次生成的值，说明太快了，sleep一下进行控速
                        # print("too fast, sleep 0.001")
                        # 如果不sleep，下次还可能会重复
                        time.sleep(0.001)
                        t = int(time.time() * 1000)
                    else:
                        cls.last_time_seq = t
                        return t
                raise Exception("too many retry")

    @classmethod
    def create_v1(cls, value):
        """v1版本是使用16进制编码的16位字符"""
        ms = cls.get_valid_ms(value)
        return struct.pack(">Q", ms).hex()


    @classmethod
    def create_v0(cls, value):
        """v0版本是一个20位固定长度的数字(19位用于毫秒时间序列)的ID"""
        t = cls.get_valid_ms(value)
        ts = "%020d" % t

        assert len(ts) == 20
        assert ts[0] == "0" # 其他数字用于扩展操作
        return ts
