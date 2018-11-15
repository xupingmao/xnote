# -*- coding: utf-8 -*-
# @author xupingmao
# @since 2017/02/19
# @modified 2018/11/14 02:00:04
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
import xauth
from logging.handlers import TimedRotatingFileHandler
from xutils import sqlite3

try:
    import psutil
except ImportError as e:
    psutil = None

def get_xnote_version():
    try:
        return xutils.readfile("version.txt")
    except:
        return ""

def get_mem_info():
    mem_used = 0
    mem_total = 0
    if psutil:
        p                 = psutil.Process(pid=os.getpid())
        mem_info          = p.memory_info()
        mem_used          = mem_info.rss
        sys_mem           = psutil.virtual_memory()
        sys_mem_used      = sys_mem.used
        sys_mem_total     = sys_mem.total
        formated_mem_size = xutils.format_size(mem_used)
    elif xutils.is_windows():
        mem_usage         = os.popen("tasklist /FI \"PID eq %s\" /FO csv" % os.getpid()).read()
        str_list          = mem_usage.split(",")
        pattern           = re.compile(r"[0-9,]+ [kK]")
        mem_list          = pattern.findall(mem_usage)
        formated_mem_size = mem_list[-1]
    else:
        # ps -C -p 10538
        formated_mem_size = ""
    return xutils.Storage(used = sys_mem_used, total = sys_mem_total)

class Item:
    def __init__(self, key, value):
        self.key   = key
        self.value = value

class handler:

    @xauth.login_required("admin")
    def GET(self):
        mem_used          = 0
        sys_mem_used      = 0
        sys_mem_total     = 0
        thread_cnt        = 0
        formated_mem_size = 0
        if psutil:
            p                 = psutil.Process(pid=os.getpid())
            mem_info          = p.memory_info()
            mem_used          = mem_info.rss
            sys_mem           = psutil.virtual_memory()
            sys_mem_used      = sys_mem.used
            sys_mem_total     = sys_mem.total
            formated_mem_size = xutils.format_size(mem_used)
        elif xutils.is_windows():
            mem_usage         = os.popen("tasklist /FI \"PID eq %s\" /FO csv" % os.getpid()).read()
            str_list          = mem_usage.split(",")
            pattern           = re.compile(r"[0-9,]+ [kK]")
            mem_list          = pattern.findall(mem_usage)
            formated_mem_size = mem_list[-1]
        else:
            formated_mem_size = ""
        thread_cnt = len(threading.enumerate())
        item_list  = [
            Item('软件版本',    get_xnote_version()),
            Item('sqlite版本', sqlite3.sqlite_version if sqlite3 != None else '')
        ]
        return xtemplate.render("system/settings.html", 
            item_list      = item_list,
            sys_mem_used   = formated_mem_size,
            sys_mem_total  = xutils.format_size(sys_mem_total),
            python_version = sys.version,
            sys_version    = platform.version(),
            processor      = platform.processor(),
            thread_cnt     = thread_cnt,
            xconfig        = xconfig,
            xnote_version  = get_xnote_version(),
            start_time     = xconfig.get("start_time"))


