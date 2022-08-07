# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-08-07 21:06:22
@LastEditors  : xupingmao
@LastEditTime : 2022-08-07 21:08:48
@FilePath     : /xnote/core/x_trace.py
@Description  : 统计相关的
"""

import time
import threading

class TraceInfo(threading.local):

    start_time = time.time()


def start_trace():
    TraceInfo.start_time = time.time()

def get_cost_time():
    return time.time() - TraceInfo.start_time

