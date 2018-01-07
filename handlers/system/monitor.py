# -*- coding: utf-8 -*-
import web
import time
import os
import sys
import platform
import xutils
import logging
import json
import threading
import re
import xtemplate
import xconfig
from logging.handlers import TimedRotatingFileHandler

try:
    import psutil
except ImportError as e:
    psutil = None

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
        formated_mem_size = xutils.format_size(mem_used)
    elif xutils.is_windows():
        mem_usage = os.popen("tasklist /FI \"PID eq %s\" /FO csv" % os.getpid()).read()
        str_list = mem_usage.split(",")
        pattern = re.compile(r"[0-9,]+ [kK]")
        mem_list = pattern.findall(mem_usage)
        formated_mem_size = mem_list[-1]
    else:
        # ps -C -p 10538
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
            formated_mem_size = xutils.format_size(mem_used)
        elif xutils.is_windows():
            mem_usage = os.popen("tasklist /FI \"PID eq %s\" /FO csv" % os.getpid()).read()
            str_list = mem_usage.split(",")
            pattern = re.compile(r"[0-9,]+ [kK]")
            mem_list = pattern.findall(mem_usage)
            formated_mem_size = mem_list[-1]
        else:
            formated_mem_size = ""
        thread_cnt = len(threading.enumerate())
        return xtemplate.render("system/monitor.html", 
            sys_mem_used = formated_mem_size,
            sys_mem_total = xutils.format_size(sys_mem_total),
            python_version = sys.version,
            sys_version = platform.version(),
            processor = platform.processor(),
            thread_cnt = thread_cnt,
            start_time = xconfig.get("start_time"))


