# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/08/22 21:54:56
# @modified 2022/03/19 10:20:23
import xauth
import xtemplate
import xutils
import sys
import platform
import xconfig
import os
import xtables
from xutils import dateutil
from xutils import fsutil
from xutils import mem_util
from xutils import Storage

try:
    import sqlite3
except ImportError:
    sqlite3 = None

try:
    import psutil
except ImportError:
    psutil = None

def get_xnote_version():
    return xconfig.SystemConfig.get_str("version")

def get_mem_info():
    mem_used = 0
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

    def __init__(self, name = "", value = "", link = "", extra_link=""):
        self.name  = name
        self.value = value
        self.link = link
        self.extra_link = extra_link

def get_db_info():
    return Storage(
        sqlite_instance_count = len(xtables.MySqliteDB._instances)
    )

def get_sys_info_detail():
    if psutil is None:
        return Storage(error = "psutil is None")
    p = psutil.Process(pid=os.getpid())
    mem_info = p.memory_info()
    sys_mem = psutil.virtual_memory()
    swap_memory = psutil.swap_memory()
    cpu_freq = psutil.cpu_freq()
    active_mem = xutils.attrget(sys_mem, "active", 0)
    inactive_mem = xutils.attrget(sys_mem, "inactive", 0)
    wired_mem = xutils.attrget(sys_mem, "wired", 0)

    return Storage(
        cpu = Storage(
            count = psutil.cpu_count(),
            freq = Storage(current = cpu_freq.current, max = cpu_freq.max, min = cpu_freq.min),
        ),
        process_mem = Storage(
            rss = xutils.format_size(mem_info.rss),
            vms = xutils.format_size(mem_info.vms),
            # memory_full_info = p.memory_full_info(),
        ),
        system_mem = Storage(
            total = xutils.format_size(sys_mem.total),
            available = xutils.format_size(sys_mem.available),
            percent = sys_mem.percent,
            used = xutils.format_size(sys_mem.used),
            free = xutils.format_size(sys_mem.free),
            active = xutils.format_size(active_mem),
            inactive = xutils.format_size(inactive_mem),
            wired = xutils.format_size(wired_mem),
        ),
        swap_memory = Storage(
            total = xutils.format_size(swap_memory.total),
            used = xutils.format_size(swap_memory.used),
            free = xutils.format_size(swap_memory.free),
            percent = swap_memory.percent,
        ),
        db_info = get_db_info(),
    )

class InfoHandler:

    @xauth.login_required("admin")
    def GET(self):
        p = xutils.get_argument("p", "")
        if p == "config_dict":
            text = xconfig.get_config_dict()
            text = xutils.tojson(text, format=True)
            return xtemplate.render("system/page/system_info_text.html", text=text)
        if p == "sys_info_detail":
            sys_info = get_sys_info_detail()
            text = xutils.tojson(sys_info, format=True)
            comment = "wired代表macOS不可被交换的内存"
            return xtemplate.render("system/page/system_info_text.html", text=text, comment_html = comment)

        mem_info = mem_util.get_mem_info()
        sys_mem_info = "%s/%s" % (mem_info.sys_mem_used, mem_info.sys_mem_total)

        items = [
            SystemInfoItem("Python版本", value = get_python_version()),
            SystemInfoItem("Xnote版本", value = get_xnote_version()),
            SystemInfoItem("应用内存使用量", value = mem_info.mem_used),
            SystemInfoItem("磁盘可用容量", get_free_data_space()),
            SystemInfoItem("数据库驱动", xconfig.DatabaseConfig.db_driver_sql, extra_link="/system/db/driver_info?type=sql"),
            SystemInfoItem("KV数据库驱动", xconfig.DatabaseConfig.db_driver_kv, extra_link="/system/db/driver_info"),
            SystemInfoItem("sqlite版本", sqlite3.sqlite_version if sqlite3 != None else ''),
            SystemInfoItem("CPU型号", platform.processor()),
            SystemInfoItem("操作系统", platform.system()),
            SystemInfoItem("操作系统版本", platform.version()),
            SystemInfoItem("系统启动时间", get_startup_time()),
            SystemInfoItem("系统配置", "查看", link = "/system/info?p=config_dict"),
            SystemInfoItem("详细系统信息", "查看", link="/system/info?p=sys_info_detail"),
            SystemInfoItem("浏览器信息", "查看", link = "/tools/browser_info"),
        ]

        return xtemplate.render("system/page/system_info.html", items = items, 
            runtime_id = xconfig.RUNTIME_ID)


xurls = (
    r"/system/info", InfoHandler
)