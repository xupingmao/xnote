# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-08-07 21:06:22
@LastEditors  : xupingmao
@LastEditTime : 2022-09-10 14:12:32
@FilePath     : /xnote/core/x_trace.py
@Description  : 统计相关的
"""

import time
import threading

class TraceInfo(threading.local):

    start_time = time.time()
    sql_logs = []


def start_trace():
    TraceInfo.start_time = time.time()
    TraceInfo.sql_logs = []

def get_cost_time():
    return time.time() - TraceInfo.start_time

def append_log(sql):
    TraceInfo.sql_logs.append(sql)

class SqlLogger:

    def append(self, sql):
        TraceInfo.sql_logs.append(sql)

