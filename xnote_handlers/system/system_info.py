# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/08/22 21:54:56
# @modified 2022/03/19 10:20:23
import sys
import platform
from turtle import onclick
import xutils
import os
import logging
import subprocess

from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xconfig
from xnote.core import xtables
from xutils import dateutil
from xutils import fsutil
from xutils import mem_util
from xutils import Storage
from xutils import webutil
from xnote_handlers.config import LinkConfig, ScriptConfig
from xnote.plugin.table_plugin import BaseTablePlugin
from xnote.plugin.sidebar import get_admin_sidebar_html
from xnote.service.lock_service import DatabaseLockService
from xnote.plugin.list_plugin import BaseListPlugin
from xnote_handlers.config.aside_config import AsideConfig
from xnote.webui import ListView, ListViewItem, Card, ActionButton, Textarea, Div

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

def get_db_info():
    return Storage(
        sqlite_instance_count = len(xtables.DBPool._sqlite_pool)
    )

def get_sys_info_detail():
    if psutil is None:
        return Storage(error = "psutil is None")
    p = psutil.Process(pid=os.getpid())
    mem_info = p.memory_info()
    sys_mem = psutil.virtual_memory()
    swap_memory = psutil.swap_memory()
    cpu_freq = psutil.cpu_freq()
    active_mem = getattr(sys_mem, "active", 0)
    inactive_mem = getattr(sys_mem, "inactive", 0)
    wired_mem = getattr(sys_mem, "wired", 0)

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

class PythonLibInfo:

    def __init__(self, name: str, lib_name: str):
        self.name = name
        self.lib_name = lib_name
        self.value = ""
        self.value_css_class = ""
        self.is_installed = False
        self.check_lib_installed()

    def check_lib_installed(self):
        try:
            __import__(self.lib_name)
            self.value = "已安装"
            self.value_css_class = "green"
            self.is_installed = True
        except:
            self.value = "未安装"
            self.value_css_class = "red"

class InfoHandler(BaseListPlugin):
    require_admin = True
    title = "系统信息"
    parent_link = LinkConfig.app_index
    
    def handle_page(self):
        p = xutils.get_argument_str("p")
        
        self.update_aside(AsideConfig.admin_aside_html)
        
        if p == "sys_info_detail":
            return self.render_sys_info_detail()
        
        if p == "python_lib":
            return self.render_python_lib()

        mem_info = mem_util.get_mem_info()
        sqlite_version = sqlite3.sqlite_version if sqlite3 != None else ''
        
        list_view = ListView()
        list_view.add(ListViewItem(text="Python版本", badge_info=get_python_version()))
        list_view.add(ListViewItem(text="Xnote版本", badge_info = get_xnote_version()))
        list_view.add(ListViewItem(text="应用内存使用量", badge_info = mem_info.mem_used))
        list_view.add(ListViewItem(text="磁盘可用容量", badge_info = get_free_data_space()))
        list_view.add(ListViewItem(text="数据库驱动", badge_info =xconfig.DatabaseConfig.db_driver_sql, 
                                   href=LinkConfig.driver_info_sql.href, show_chevron_right=True, css_class="black"))
        list_view.add(ListViewItem(text="KV数据库驱动", badge_info =xconfig.DatabaseConfig.db_driver_kv, 
                                   href=LinkConfig.driver_info_kv.href, show_chevron_right=True, css_class="black"))
        list_view.add(ListViewItem(text="sqlite版本", badge_info = sqlite_version))
        list_view.add(ListViewItem(text="CPU型号", badge_info = platform.processor()))
        list_view.add(ListViewItem(text="操作系统", badge_info = platform.system()))
        list_view.add(ListViewItem(text="操作系统版本", badge_info = platform.version()))
        list_view.add(ListViewItem(text="系统启动时间", badge_info = get_startup_time()))
        list_view.add(ListViewItem(text="启动配置", badge_info = "查看", href = "/system/info/boot_config", show_chevron_right=True, css_class="black"))
        list_view.add(ListViewItem(text="Python第三方库", badge_info = "查看", href = "/system/info?p=python_lib", show_chevron_right=True, css_class="black"))
        list_view.add(ListViewItem(text="详细系统信息", badge_info = "查看", href = "/system/info?p=sys_info_detail", show_chevron_right=True, css_class="black"))
        list_view.add(ListViewItem(text="浏览器信息", badge_info = "查看", href = "/tools/browser_info", show_chevron_right=True, css_class="black"))

        # 重启
        list_item = ListViewItem(text="重启系统")
        list_item.extra.add(ActionButton(text="重启", onclick="javascript:xnote.admin.onRestart()", css_class="btn danger"))
        list_view.add(list_item)
        
        # 升级
        list_item = ListViewItem(text="升级系统")
        list_item.extra.add(ActionButton(text="升级", onclick="javascript:xnote.admin.onUpgrade()", css_class="btn danger"))
        list_view.add(list_item)
        
        card = Card()
        card.add(list_view)
        
        self.set_html_var("runtimeId", xconfig.RUNTIME_ID)
        self.load_script(ScriptConfig.admin_js)
        self.add_component(card)
    
    def render_sys_info_detail(self):
        self.title = "详细系统信息"
        self.parent_link = LinkConfig.system_info
        
        sys_info = get_sys_info_detail()
        text = xutils.tojson(sys_info, format=True)
        comment = "wired代表macOS不可被交换的内存"
        
        card = Card()
        card.add(Textarea(value=text, css_class="row", rows="30"))
        card.add(Div(css_class="info light", html = comment))
        self.add_component(card)
        
    def render_python_lib(self):
        self.title = "Python第三方库"
        self.parent_link = LinkConfig.system_info
        
        item_list = [
            PythonLibInfo("Pillow", "PIL"),
            PythonLibInfo("markdown", "markdown"),
            PythonLibInfo("beautifulsoup4", "bs4"),
            PythonLibInfo("requests", "requests"),
            PythonLibInfo("wsgidav", "wsgidav"),
            PythonLibInfo("psutil", "psutil"),
            PythonLibInfo("leveldb", "leveldb"),
            PythonLibInfo("pyperclip", "pyperclip"),
        ]
        html = xtemplate.render(
            "system/page/system_info_list.html",
            title="Python第三方库",
            parent_link = LinkConfig.system_info,
            item_list=item_list,
        )
        
        self.write_plain_html(html)

class BootConfigHandler(BaseTablePlugin):
    require_admin = True
    title = "启动配置"
    parent_link = LinkConfig.system_info

    def handle_page(self):
        self.write_aside(get_admin_sidebar_html())
        table = self.create_table()
        table.add_head("配置项", "name")
        table.add_head("类型", "type", width="50px")
        table.add_head("值", "value")

        type_dict = {}
        value_dict = {}

        for key, value in xconfig.get_config_dict().items():
            assert isinstance(key, str)
            if key.endswith(".type"):
                type_dict[key] = value
            else:
                value_dict[key] = value
        
        for key, value in value_dict.items():
            row = dict(name = key, value = value, type = type_dict.get(f"{key}.type", ""))
            table.add_row(row)
        kw = Storage()
        kw.table = table
        return self.response_page(**kw)


class InstallLibHandler:

    @xauth.admin_required()
    def POST(self):
        lib_name = xutils.get_argument_str("lib_name")
        logging.info("start to install lib %s", lib_name)
        with DatabaseLockService.lock(lock_key= "install_lib", timeout_seconds=600) as lock:
            install_cmd = [sys.executable, "-m", "pip", "install", lib_name]
            # 安装指定库
            result = subprocess.check_call(
                install_cmd,
                stdout=subprocess.PIPE,  # 捕获标准输出
                stderr=subprocess.PIPE,  # 捕获错误输出
                encoding="utf-8"
            )
            # TODO 写入安装日志到缓存
            if result == 0:
                return webutil.SuccessResult()
            else:
                return webutil.FailedResult("500", message=f"status_code: {result}")
        return webutil.SuccessResult()

xurls = (
    r"/system/info", InfoHandler,
    r"/system/info/boot_config", BootConfigHandler,
    r"/system/install_python_lib", InstallLibHandler,
)