# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/08/22 21:54:56
# @modified 2022/02/26 10:40:22
import xauth
import xtemplate
import xutils
import os
import re
import sys
import platform
import xconfig
from xutils import dateutil
from xutils import fsutil
from xutils import Storage
from xutils import mem_util

try:
    import sqlite3
except ImportError:
    sqlite3 = None

def get_xnote_version():
    return xconfig.get_global_config("system.version")


def get_mem_info():
    mem_used = 0
    mem_total = 0
    result = mem_util.get_mem_info()

    mem_used = result.mem_used
    sys_mem_used = result.sys_mem_used
    sys_mem_total = result.sys_mem_total
    return "%s/%s/%s" % (mem_used, sys_mem_used, sys_mem_total)

def get_python_version():
    return sys.version

def get_startup_time():
    return dateutil.format_time(xconfig.START_TIME)

def get_free_data_space():
    try:
        size = fsutil.get_free_space(xconfig.get_system_dir("data"))
        return xutils.format_size(size)
    except:
        xutils.print_exc()
        return "<未知>"

class SystemInfoItem:

    def __init__(self, name = "", value = ""):
        self.name  = name
        self.value = value

class InfoHandler:

    @xauth.login_required("admin")
    def GET(self):
        items = [
            SystemInfoItem("Python版本", value = get_python_version()),
            SystemInfoItem("Xnote版本", value = get_xnote_version()),
            SystemInfoItem("内存信息", value = get_mem_info()),
            SystemInfoItem("磁盘可用容量", get_free_data_space()),
            SystemInfoItem("sqlite版本", sqlite3.sqlite_version if sqlite3 != None else ''),
            SystemInfoItem("CPU型号", platform.processor()),
            SystemInfoItem("操作系统", platform.system()),
            SystemInfoItem("操作系统版本", platform.version()),
            SystemInfoItem("系统启动时间", get_startup_time()),
        ]

        return xtemplate.render("system/page/system_info.html", items = items, 
            runtime_id = xconfig.RUNTIME_ID)


xurls = (
    r"/system/info", InfoHandler
)