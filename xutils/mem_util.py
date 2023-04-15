# -*- coding:utf-8 -*-
# @author mark
# @since 2022/02/20 22:36:31
# @modified 2022/03/08 23:22:45
# @filename mem_util.py

import os
import re
import logging
import time

try:
    import psutil
except ImportError:
    psutil = None

import xutils
from xutils.base import Storage

_ignored_name_set = set()
_ignored_group_set = set()

def get_mem_info_by_psutil():
    p                 = psutil.Process(pid=os.getpid())
    mem_info          = p.memory_info()
    mem_used          = xutils.format_size(mem_info.rss)
    sys_mem           = psutil.virtual_memory()
    sys_mem_used      = xutils.format_size(sys_mem.used)
    sys_mem_total     = xutils.format_size(sys_mem.total)
    if xutils.is_mac():
        sys_mem_used = xutils.format_size(sys_mem.total * sys_mem.percent / 100)
    return Storage(mem_used = mem_used, sys_mem_used = sys_mem_used, sys_mem_total = sys_mem_total)

def get_mem_info_by_tasklist():
    mem_usage         = os.popen("tasklist /FI \"PID eq %s\" /FO csv" % os.getpid()).read()
    str_list          = mem_usage.split(",")
    pattern           = re.compile(r"[0-9,]+ [kK]")
    mem_list          = pattern.findall(mem_usage)
    if len(mem_list) > 0:
        formated_mem_size = mem_list[-1]
    else:
        formated_mem_size = "-1"
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

def ignore_log_mem_info_deco(name=None, group=None):
    if name != None:
        _ignored_name_set.add(name)
    if group != None:
        _ignored_group_set.add(group)

def log_mem_info_deco(name, log_args = False, group = "default"):
    """打印内存日志的装饰器"""

    def deco(func):
        if name in _ignored_name_set:
            return func
        if group in _ignored_group_set:
            return func 

        def handle(*args, **kw):
            args0 = ""
            before = 0
            
            try:
                before = get_mem_info().mem_used
                return func(*args, **kw)
            finally:
                if log_args:
                    args0 = args
                after = get_mem_info().mem_used
                logging.debug("(%s)%s|mem_used:%s -> %s", name, args0, before, after)
        return handle
    return deco


class MemLogger:

    def __init__(self, name, args = ""):
        self.name = name
        self.start_time = time.time()
        self.prev_time = self.start_time
        self.args = args
        self.start_mem = get_mem_info().mem_used
        self.prev_mem = self.start_mem

    def done(self):
        current = get_mem_info().mem_used
        cost_time = int((time.time() - self.start_time) * 1000)
        logging.debug("(%s)%s|mem_used:%s -> %s (%sms)", self.name, self.args, 
            self.start_mem, current, cost_time)

    def info(self, message):
        current = get_mem_info().mem_used
        cost_time = int((time.time() - self.prev_time) * 1000)

        logging.debug("(%s)%s|%s|mem_used:%s -> %s (%sms)", 
            self.name, self.args, message,
            self.prev_mem, current, cost_time) 

        self.prev_mem = current
        self.prev_time = time.time()


