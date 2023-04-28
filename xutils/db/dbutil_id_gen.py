# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-10-03 22:51:40
@LastEditors  : xupingmao
@LastEditTime : 2023-04-28 22:19:53
@FilePath     : /xnote/xutils/db/dbutil_id_gen.py
@Description  : id生成
"""
from __future__ import print_function
from __future__ import absolute_import

import time
import xutils
try:
    from xutils.db import dbutil_base as base
except ImportError:
    import dbutil_base as base
from xutils.db.encode import encode_id

class IdGenerator:

    def __init__(self, table_name):
        self.table_name = table_name

    def create_increment_id(self, start_id=None):
        if start_id != None:
            assert start_id > 0

        max_id_key = "_max_id:" + self.table_name

        with base.get_write_lock():
            new_id = 0
            last_id = base.db_get(max_id_key) # type: int
            if last_id is None:
                if start_id != None:
                    new_id = start_id
                else:
                    new_id = 1
            else:
                new_id = last_id + 1
            base.db_put(max_id_key, new_id)
            return encode_id(new_id)

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

        if id_value != None:
            base.validate_none(id_type, "invalid id_type")
            return id_value

        raise Exception("unknown id_type:%s" % id_type)



class TimeSeqId:

    """时间序列ID生成器,第1位数字用于标识ID版本,不保证定长"""

    LAST_TIME_SEQ = -1

    @classmethod
    def create(cls, value):
        """生成一个时间序列
        @param {float|None} value 时间序列，单位是秒，可选
        @return {string}    20位的时间序列
        """
        return cls.create_v0(value)

    @classmethod
    def create_v0(cls, value):
        """v0版本是一个20位固定长度的数字(19位用于毫秒时间序列)的ID"""
        if value != None:
            error_msg = "expect <class 'float'> but see %r" % type(value)
            assert isinstance(value, float), error_msg

            value = int(value * 1000)
            ts = "%020d" % value
        else:
            t = int(time.time() * 1000)
            # 加锁防止并发生成一样的值
            # 注意这里的锁是单个进程级别的,后续可以考虑分布式锁,在时间戳后面增加机器的编号用于防止重复
            with base.get_write_lock("time_seq"):
                if t == cls.LAST_TIME_SEQ:
                    # 等于上次生成的值，说明太快了，sleep一下进行控速
                    # print("too fast, sleep 0.001")
                    # 如果不sleep，下次还可能会重复
                    time.sleep(0.001)
                    t = int(time.time() * 1000)
                cls.LAST_TIME_SEQ = t
                ts = "%020d" % t
        
        assert len(ts) == 20
        assert ts[0] == "0" # 其他数字用于扩展操作
        return ts
