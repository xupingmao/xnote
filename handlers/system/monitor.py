# -*- coding: utf-8 -*-

import web
import time
import os
import xutils
import logging
from logging.handlers import TimedRotatingFileHandler
import json
import threading
import re
import xtemplate

try:
    import psutil
except ImportError as e:
    psutil = None

sys = xutils.sys

def format_size(size):
    if size < 1024:
        return '%s B' % size
    elif size < 1024 **2:
        return '%.2f K' % (float(size) / 1024)
    elif size < 1024 ** 3:
        return '%.2f M' % (float(size) / 1024 ** 2)
    else:
        return '%.2f G' % (float(size) / 1024 ** 3)

def get_mem_info():
    mem_used = 0
    mem_total = 0
    if psutil:
        p = psutil.Process(pid=os.getpid())
        mem_info = p.memory_info()
        mem_used = mem_info.rss
        sys_mem = psutil.virtual_memory()
        sys_mem_used = sys_mem.used
        sys_mem_total = sys_mem.total
        formated_mem_size = format_size(mem_used)
    elif xutils.is_windows():
        mem_usage = os.popen("tasklist /FI \"PID eq %s\" /FO csv" % os.getpid()).read()
        str_list = mem_usage.split(",")
        pattern = re.compile(r"[0-9,]+ [kK]")
        mem_list = pattern.findall(mem_usage)
        # print(mem_list)
        # mem_used = int(str_list[1])
        formated_mem_size = mem_list[-1]
    else:
        formated_mem_size = ""
    return xutils.Storage(used = sys_mem_used, total = sys_mem_total)

class handler:

    def GET(self):
        mem_used = 0
        sys_mem_used = 0
        sys_mem_total = 0
        thread_cnt = 0
        formated_mem_size = 0
        if psutil:
            p = psutil.Process(pid=os.getpid())
            mem_info = p.memory_info()
            mem_used = mem_info.rss
            sys_mem = psutil.virtual_memory()
            sys_mem_used = sys_mem.used
            sys_mem_total = sys_mem.total
            formated_mem_size = format_size(mem_used)
        elif xutils.is_windows():
            mem_usage = os.popen("tasklist /FI \"PID eq %s\" /FO csv" % os.getpid()).read()
            str_list = mem_usage.split(",")
            pattern = re.compile(r"[0-9,]+ [kK]")
            mem_list = pattern.findall(mem_usage)
            # print(mem_list)
            # mem_used = int(str_list[1])
            formated_mem_size = mem_list[-1]
        else:
            formated_mem_size = ""
        thread_cnt = len(threading.enumerate())
        return xtemplate.render("system/monitor.html", 
            sys_mem_used = formated_mem_size,
            sys_mem_total = format_size(sys_mem_total),
            python_version = sys.version,
            thread_cnt = thread_cnt)


    def POST(self):
        pass
