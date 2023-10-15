# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-08-07 21:06:22
@LastEditors  : xupingmao
@LastEditTime : 2022-09-25 23:33:31
@FilePath     : /xnote/core/x_trace.py
@Description  : 统计相关的
"""

import time
import threading
from xutils import Storage
from xutils.interfaces import SqlLoggerInterface

class TraceInfo(threading.local):

    def __init__(self):
        self.start_time = time.time()
        self.sql_logs = []

_trace_info = TraceInfo()

def start_trace():
    _trace_info.start_time = time.time()
    _trace_info.sql_logs = []

def get_cost_time():
    return time.time() - _trace_info.start_time

class SqlLogger(SqlLoggerInterface):

    def append(self, sql):
        _trace_info.sql_logs.append(sql)


def get_debug_info():
    info = Storage()
    info.sql_logs = _trace_info.sql_logs
    return info
