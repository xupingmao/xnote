# -*- coding:utf-8 -*-
# @author mark
# @since 2022/04/03 20:20:57
# @modified 2022/04/03 22:17:05
# @filename system_boot.py

import webbrowser
import threading
import time
import xutils
import tracemalloc

from xnote.core import xmanager
from xnote.core import xconfig
from xnote.core import xauth
from tracemalloc import Snapshot
from xnote.plugin import BasePluginV2, TabBox, Card, DataTable, TextSpan, Textarea
from xnote_handlers.config import LinkConfig
from xnote.service.system_meta_service import SystemMetaEnum
from xutils import mem_util, _sqlite_mem

_boot_snapshot = None
_boot_mem_info = None

if xconfig.WebConfig.ringtone:
    xutils.say("系统已经启动上线")


# 启动打开浏览器选项
if xconfig.WebConfig.open_browser:
    class OpenThread(threading.Thread):
        def run(self):
            time.sleep(2)
            webbrowser.open("http://localhost:%s/" % xconfig.PORT)

    thread = OpenThread()
    thread.start()

if SystemMetaEnum.trace_malloc_enabled.bool_value:
    tracemalloc.start()
    _boot_snapshot = tracemalloc.take_snapshot()
    _boot_mem_info = mem_util.get_mem_info()


@xmanager.listen("sys.init")
def boot_onload(ctx):
    print(ctx)


class TraceMallocHandler(BasePluginV2):
    """内存分析：
    1. 内存快照（tracemalloc 启动前后的内存差异）
    2. SQLite 内存（遍历已注册的 SQLite 连接，统计各连接内存占用）
    """
    require_admin = True
    title = "内存分析"
    rows = 0
    parent_link = LinkConfig.system_plugin_index

    def handle(self, input=""):
        tab = xutils.get_argument_str("tab", "tracemalloc")
        self.render_tab_box(tab)
        if tab == "sqlite":
            self.render_sqlite_memory()
        else:
            self.render_tracemalloc()

    def render_tab_box(self, current: str):
        tab = TabBox(tab_key="tab", tab_default=current)
        tab.add_item("内存快照", value="tracemalloc",
                     href="/system/trace_malloc?tab=tracemalloc")
        tab.add_item("SQLite内存", value="sqlite",
                     href="/system/trace_malloc?tab=sqlite")
        card = Card()
        card.add(tab)
        self.add_component(card)

    def render_tracemalloc(self):
        if _boot_snapshot is None:
            card = Card()
            card.add(TextSpan(text="trace malloc not enabled"))
            self.add_component(card)
            return
        current = tracemalloc.take_snapshot()
        diff = current.compare_to(_boot_snapshot, "lineno")
        lines = []
        lines.append("boot_mem_info:" + str(_boot_mem_info))
        lines.append("current_mem_info:" + str(mem_util.get_mem_info()))
        for item in diff[:20]:
            lines.append(str(item))
        card = Card()
        card.add(Textarea("\n".join(lines), css_class="row", rows="20"))
        self.add_component(card)

    def render_sqlite_memory(self):
        """展示 SQLite 总内存占用与每个采样到的连接（按数据库文件聚合）的内存占用。

        统计来自 DAO 访问入口（TableProxy.select / SqliteKV.Get）的随机采样，
        默认 10% 命中率，命中时记录当前线程连接的内存占用，无需手动注册连接。
        """
        total = _sqlite_mem.get_total_memory_usage()
        items = _sqlite_mem.get_stats()
        card = Card()
        card.add(TextSpan(
            text="SQLite 采样总内存占用: " + xutils.format_size(total),
            css_class="mb-2"))
        if _sqlite_mem.MEMORY_USED_AVAILABLE:
            card.add(TextSpan(
                text="（精确值：PRAGMA memory_used）", css_class="mb-2"))
        else:
            card.add(TextSpan(
                text="（当前 SQLite 未开启 ENABLE_MEMORY_MANAGEMENT，无法获取真实内存；每行“数据占用”为该连接对应数据库文件大小(page_size*page_count)，属共享资源，故总内存按数据库文件去重求和，不等于各行之和，仅供参考）",
                css_class="mb-2"))
        if len(items) == 0:
            card.add(TextSpan(
                text="暂无采样数据（访问任意 SQLite 页面/接口触发随机采样后会出现，默认 10% 命中率）"))
        else:
            table = DataTable()
            table.add_head("连接ID", "conn_id")
            table.add_head("数据库文件", "db_file")
            table.add_head("数据占用(估算)", "memory")
            table.add_head("最近采样时间", "update_time")
            for item in items:
                table.add_row(dict(
                    conn_id=item.conn_id,
                    db_file=item.db_file,
                    memory=xutils.format_size(item.memory),
                    update_time=item.update_time_str))
            card.add(table)
        self.add_component(card)


xurls = (
    "/system/trace_malloc", TraceMallocHandler,
)