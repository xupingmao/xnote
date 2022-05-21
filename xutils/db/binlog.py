# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-04 19:55:32
@LastEditors  : xupingmao
@LastEditTime : 2022-05-21 20:42:40
@FilePath     : /xnote/xutils/db/binlog.py
@Description  : 数据库的binlog,用于同步
"""

from xutils import dbutil
from xutils.db.dbutil_table import db_put, prefix_list

import threading

def _format_log_id(log_id):
    return "%020d" % log_id

class BinLog:

    dbutil.register_table("_binlog", "数据同步的binlog")
    _table_name = "_binlog"
    _lock = threading.RLock()
    _instance = None

    def __init__(self) -> None:
        """正常要使用单例模式使用"""
        with self._lock:
            if self._instance != None:
                raise Exception("只能创建一个BinLog单例")
            self._instance = self

        last_key  = self.last_key()
        if last_key == None:
            self.last_seq = 0
        else:
            self.last_seq = int(last_key)
    
    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance == None:
                cls._instance = BinLog()
            return cls._instance
    
    def get_record_key(self, log_id):
        return self._table_name + ":" + log_id
    
    def last_key(self):
        logs = prefix_list(self._table_name, reverse = True, limit = 1, include_key = True)
        if len(logs) == 0:
            return None
        key, value = logs[0]
        return key.split(":")[1]
    
    def _put_log(self, log_id, log_body, batch = None):
        key = self.get_record_key(log_id)
        # print("binlog(%s,%s)" % (key, log_body))
        if batch != None:
            batch.put(key, log_body)
        else:
            db_put(key, log_body)

    def add_log(self, optype, key, value = None, batch = None):
        with self._lock:
            self.last_seq += 1
            binlog_id = _format_log_id(self.last_seq)
            binlog_body = dict(optype = optype, key = key)
            self._put_log(binlog_id, binlog_body, batch=batch)



