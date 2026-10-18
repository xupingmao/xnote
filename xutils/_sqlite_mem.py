# -*- coding: utf-8 -*-
"""SQLite 内存占用统计工具

通过随机采样统计 SQLite 连接的内存占用，避免每次请求都执行 PRAGMA 带来额外开销。

做法：在 DAO 访问入口（TableProxy.select / SqliteKV.Get）按默认 10% 的概率触发采样，
采样命中时读取“当前线程连接”的内存信息（PRAGMA memory_used，不可用时退化为
page_count * page_size 估算），并以“连接”维度（id(conn)）记录到线程安全的全局统计表。

说明：
- 统计表以连接为维度，同一个数据库文件可以对应多个连接，每个连接各自记录一份内存占用。
- 连接是短生命周期对象，进程内无法对其建立弱引用（sqlite3.Connection 不可弱引用），
  这里改用“最近刷新时间 + TTL”剔除已销毁连接，避免统计表无限膨胀。
- 部分 SQLite 发行版（如 Windows Store 版 Python）未开启 ENABLE_MEMORY_MANAGEMENT，
  PRAGMA memory_used 不返回任何行，此时自动退化为按页估算的数据占用。
- 本模块不依赖任何上层配置，采样开关（_ENABLED）由上层在初始化或配置变更时通过
  set_enabled 设置（见管理员设置页面的 SystemMetaEnum.sqlite_mem_sample_enabled）。
"""

import sqlite3
import threading
import random
import time
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

# 采样默认触发概率
DEFAULT_PROBABILITY = 0.1

# 采样记录过期时间（秒）：超过该时间未被刷新的连接视为已销毁，读取时剔除
STATS_TTL = 120

# 功能开关：是否在 DAO 入口随机采样连接内存占用。
# 由管理员设置页面（SystemMetaEnum.sqlite_mem_sample_enabled）控制，
# 在初始化或配置变更时通过 set_enabled 更新本模块开关，默认开启。
_ENABLED = True


def is_enabled() -> bool:
    """当前是否开启连接内存采样。"""
    return _ENABLED


def set_enabled(value) -> None:
    """设置采样开关。接受 bool 或字符串（"1"/"true"/"yes"/"on" 视为开启）。

    由上层（xconfig 初始化 / 管理员设置页变更）调用，本模块不依赖 SystemMeta。
    """
    global _ENABLED
    if isinstance(value, str):
        _ENABLED = value.lower() in ("1", "true", "yes", "on")
    else:
        _ENABLED = bool(value)


@dataclass
class ConnMemoryStat:
    """单个连接的内存采样记录（连接维度）。"""
    conn_id: int = 0
    db_file: str = ""
    memory: int = 0
    update_time: float = 0.0
    update_time_str: str = ""


def _probe_memory_used():
    # 探测当前 SQLite 是否支持 PRAGMA memory_used（需要 ENABLE_MEMORY_MANAGEMENT）
    try:
        c = sqlite3.connect(":memory:")
        try:
            return c.execute("PRAGMA memory_used").fetchone() is not None
        finally:
            c.close()
    except Exception:
        return False


# 当前 SQLite 是否支持精确内存统计；Windows Store 版 Python 常未开启
MEMORY_USED_AVAILABLE = _probe_memory_used()


# 线程安全的统计表：conn_id -> 采样记录（连接维度）
_stats_lock = threading.Lock()
_stats: Dict[int, ConnMemoryStat] = {}


def _query_memory(conn) -> int:
    """查询单个连接的内存/数据占用（字节）。

    优先 PRAGMA memory_used；不可用时退化为 PRAGMA page_count * page_size 估算。
    """
    try:
        cursor = conn.cursor()
        try:
            if MEMORY_USED_AVAILABLE:
                cursor.execute("PRAGMA memory_used")
                row = cursor.fetchone()
                if row is not None and row[0] is not None:
                    return int(row[0])
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()
            pc = int(page_count[0]) if page_count and page_count[0] is not None else 0
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()
            ps = int(page_size[0]) if page_size and page_size[0] is not None else 0
            return pc * ps
        finally:
            cursor.close()
    except Exception:
        logging.warning("sample sqlite memory failed", exc_info=True)
        return 0


def _get_main_db_file(conn) -> str:
    """获取连接对应的主数据库文件路径（用于展示）。"""
    try:
        cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA database_list")
            row = cursor.fetchone()
        finally:
            cursor.close()
        if row is not None and len(row) >= 3:
            return row[2]
        return "?"
    except Exception:
        return "?"


def sample_current_connection(conn, probability: float = DEFAULT_PROBABILITY) -> int:
    """按 probability 的概率采样当前连接的内存占用并记录到全局统计表（连接维度）。

    命中返回采样到的字节数；未命中（随机数 >= 概率）直接返回 0，表示本次未采样。
    功能被关闭（_ENABLED 为 False）时直接返回 0，不进行任何采样。
    """
    if not _ENABLED:
        return 0
    if random.random() >= probability:
        return 0
    memory = _query_memory(conn)
    now = time.time()
    stat = ConnMemoryStat(
        conn_id=id(conn),
        db_file=_get_main_db_file(conn),
        memory=memory,
        update_time=now,
        update_time_str=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
    )
    with _stats_lock:
        _stats[stat.conn_id] = stat
    return memory


def _prune_locked(now: Optional[float] = None) -> None:
    """剔除超过 TTL 未刷新的连接记录，避免统计表无限膨胀。调用方需持有 _stats_lock。"""
    if now is None:
        now = time.time()
    expired = [cid for cid, item in _stats.items()
               if now - item.update_time > STATS_TTL]
    for cid in expired:
        del _stats[cid]


def get_stats() -> List[ConnMemoryStat]:
    """返回最近一次采样结果列表（连接维度，同一个 db_file 可有多条）。"""
    with _stats_lock:
        _prune_locked()
        return list(_stats.values())


def get_total_memory_usage() -> int:
    """返回 SQLite 内存占用总量（字节）。

    - 若支持 PRAGMA memory_used：该值是进程级全局值，所有连接取到的结果相同，
      直接取其一（不可跨连接累加，否则会重复计算）。
    - 若不支持（退化为 page_count * page_size，即数据库文件大小）：同一数据库文件
      可被多个连接打开，属共享资源，需按 db_file 去重后再求和，避免被重复累加。
    """
    with _stats_lock:
        _prune_locked()
        items = list(_stats.values())
    if not items:
        return 0
    if MEMORY_USED_AVAILABLE:
        return max(item.memory for item in items)
    file_size_map = {}
    for item in items:
        file_size_map[item.db_file] = item.memory
    return sum(file_size_map.values())


def reset_stats() -> None:
    """清空统计（主要用于测试隔离）。"""
    with _stats_lock:
        _stats.clear()
