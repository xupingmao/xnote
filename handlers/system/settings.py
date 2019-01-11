# -*- coding: utf-8 -*-
# @author xupingmao
# @since 2017/02/19
# @modified 2019/01/11 01:04:03
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
import xtables
from logging.handlers import TimedRotatingFileHandler
from xutils import sqlite3, Storage

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

class SettingsHandler:

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
            show_aside     = False,
            html_title     = "系统设置",
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



class StorageHandler:
    """基于数据库的配置"""

    @xauth.login_required()
    def GET(self):
        key  = xutils.get_argument("key")
        db = xtables.get_storage_table()
        config = db.select_one(where=dict(key=key, user=xauth.get_current_name()))
        if config is None:
            config = Storage(key=key, value="")
        return xtemplate.render("system/properties.html", 
            action = "/system/storage",
            show_aside = False,
            config = config)
    
    @xauth.login_required()
    def POST(self):
        key = xutils.get_argument("key")
        value = xutils.get_argument("value")
        user = xauth.get_current_name()
        db = xtables.get_storage_table()
        config = db.select_one(where=dict(key=key, user=user))
        if config is None:
            db.insert(user = user, key = key, value = value, 
                ctime = xutils.format_datetime(), 
                mtime = xutils.format_datetime())
        else:
            db.update(value=value, mtime = xutils.format_datetime(), where=dict(key=key, user=user))

        config = Storage(key = key, value = value)
        return xtemplate.render("system/properties.html", 
            action = "/system/storage",
            show_aside = False,
            config = config)

DEFAULT_SETTINGS = '''

# 导航配置
[NAV_LIST]
About = /code/wiki/README.md


# 索引目录
[INDEX_DIRS]


'''

class PropertiesHandler:
    """基于缓存的配置"""

    @xauth.login_required()
    def GET(self):
        key  = xutils.get_argument("key")
        user = xauth.get_current_name()
        default_value = ""

        if key == "settings":
            default_value = DEFAULT_SETTINGS

        config = Storage(key = key, value = xutils.cache_get("%s@prop_%s" % (user, key), 
            default_value))

        if config is None:
            config = Storage(key=key, value="")
        return xtemplate.render("system/properties.html", 
            show_aside = False,
            config = config)
    
    @xauth.login_required()
    def POST(self):
        key = xutils.get_argument("key")
        value = xutils.get_argument("value")
        user = xauth.get_current_name()
        
        xutils.cache_put("%s@prop_%s" % (user, key), value)

        if key == "settings":
            self.update_settings(value)
        
        config = Storage(key = key, value = value)
        return xtemplate.render("system/properties.html", 
            show_aside = False,
            config = config)

    def update_settings(self, config_text):
        from xutils import ConfigParser

        nav_list = []

        cf = ConfigParser()
        cf.read_string(config_text)
        names = cf.sections()

        options = cf.options('NAV_LIST')
        for option in options:
            value = cf.get('NAV_LIST', option)
            nav_list.append(Storage(name = option, url = value))

        # 处理导航        
        xconfig.NAV_LIST = nav_list


xurls = (
    r"/system/settings", SettingsHandler,
    r"/system/properties", PropertiesHandler,
    r"/system/storage", StorageHandler
)
