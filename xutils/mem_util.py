# -*- coding:utf-8 -*-
# @author mark
# @since 2022/02/20 22:36:31
# @modified 2022/02/20 23:01:19
# @filename mem_util.py

import os
import re
import logging

try:
    import psutil
except ImportError:
    psutil = None

import xutils
from xutils.base import Storage


def get_mem_info_by_psutil():
    p                 = psutil.Process(pid=os.getpid())
    mem_info          = p.memory_info()
    mem_used          = xutils.format_size(mem_info.rss)
    sys_mem           = psutil.virtual_memory()
    sys_mem_used      = xutils.format_size(sys_mem.used)
    sys_mem_total     = xutils.format_size(sys_mem.total)
    return Storage(mem_used = mem_used, sys_mem_used = sys_mem_used, sys_mem_total = sys_mem_total)

def get_mem_info_by_tasklist():
    mem_usage         = os.popen("tasklist /FI \"PID eq %s\" /FO csv" % os.getpid()).read()
    str_list          = mem_usage.split(",")
    pattern           = re.compile(r"[0-9,]+ [kK]")
    mem_list          = pattern.findall(mem_usage)
    formated_mem_size = mem_list[-1]
    return Storage(mem_used = formated_mem_size, sys_mem_used = "-1", sys_mem_total = "-1")

def get_mem_info():
    if psutil:
        result = get_mem_info_by_psutil()
    elif xutils.is_windows():
        result = get_mem_info_by_tasklist()
    else:
        # ps -C -p 10538
        result = Storage(mem_used = "-1", sys_mem_used = "-1", sys_mem_total = "-1")
    return result

def log_mem_info_deco(name):
    """打印内存日志的装饰器"""
    def deco(func):
        def handle(*args, **kw):
            try:
                logging.debug("(%s) start|mem_info:%s", name, get_mem_info())
                return func(*args, **kw)
            finally:
                logging.debug("(%s) done|mem_info:%s", name, get_mem_info())
        return handle
    return deco
