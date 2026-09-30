# -*- coding:utf-8 -*-
"""
table_plugin / list_plugin 渲染性能基准测试脚本

测量两个插件体系在数据量增长时的 HTML 渲染开销:
  1. DataTable.render()        —— table_plugin 的核心数据表格渲染（按行拼装 HTML）
  2. ListView.render()         —— list_plugin 的核心列表渲染（按 item 拼装 HTML）
  3. TablePlugin 整页渲染      —— BaseTablePlugin.response_page（插件模板 include + 表格渲染）
  4. ListPlugin 整页渲染       —— BaseListPlugin.response_page（插件模板 include + 列表渲染）

用法（在项目根目录执行）:
    python scripts/benchmark_render.py
    python scripts/benchmark_render.py --rows 100,1000,5000,10000 --iters 10
    python scripts/benchmark_render.py --csv result.csv   # 同时导出 CSV

说明:
  - 复用 tests.test_base 的 bootstrap 来初始化模板加载器（xtemplate.reload），
    组件 render 不需要 HTTP 请求上下文（webui 单测已验证可直接调用 .render()）。
  - 每个场景: 先 warmup 1 次（触发模板编译），再跑 iters 次取统计值。
  - 只统计「渲染」本身耗时（组件/数据在计时循环外预构建一次），避免把数据准备算进去。
"""
import os
import sys
import time
import argparse
import statistics

# 项目根目录加入 sys.path，保证 scripts/ 下也能 import 项目模块
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# 初始化模板加载器（必备，否则 xtemplate.render 找不到模板）
from tests.test_base import init as bootstrap_app  # noqa: E402
bootstrap_app()

from xutils import Storage  # noqa: E402
from xnote.plugin import DataTable, TableActionType  # noqa: E402
from xnote.plugin.table_plugin import BaseTablePlugin  # noqa: E402
from xnote.plugin.list_plugin import BaseListPlugin  # noqa: E402
from xnote.webui import ListView, ListViewItem  # noqa: E402


# ----------------------------------------------------------------------
# 数据构造（贴近真实插件的字段结构，便于反映真实渲染开销）
# ----------------------------------------------------------------------
def build_data_table(n: int) -> DataTable:
    """构造一个有 n 行的 DataTable，字段/操作与真实 table_plugin 一致"""
    table = DataTable()
    table.add_head("类型", "type", css_class_field="type_class")
    table.add_head("标题", "title", link_field="view_url")
    table.add_head("日期", "date")
    table.add_head("内容", "content")
    table.add_action("编辑", link_field="edit_url", type=TableActionType.edit_form)
    table.add_action("删除", link_field="delete_url", type=TableActionType.confirm,
                     msg_field="delete_msg", css_class="btn danger")
    for i in range(n):
        row = {
            "type": "类型1",
            "title": f"测试标题-{i}",
            "type_class": "red",
            "date": "2020-01-01",
            "content": f"测试内容-{i}",
            "view_url": "/note/index",
            "edit_url": f"?action=edit&id={i}",
            "delete_url": f"?action=delete&id={i}",
            "delete_msg": "确认删除记录吗?",
        }
        table.add_row(row)
    return table


def build_list_view(n: int) -> ListView:
    """构造一个有 n 个 item 的 ListView，字段与真实 list_plugin 一致"""
    lv = ListView()
    for i in range(n):
        lv.add_item(ListViewItem(
            text=f"row{i}",
            badge_info=f"test-{i}",
            icon_class="fa fa-file-text-o",
            show_chevron_right=True))
    return lv


class _BenchTablePlugin(BaseTablePlugin):
    """只用于整页渲染基准，复用 response_page，避免数据准备计入耗时"""

    def render_page(self, table: DataTable):
        self.html = ""  # 每次重置, 保证返回的体量就是单次渲染结果
        kw = Storage()
        kw.table = table
        kw.page = 1
        kw.page_url = "?page="
        self.response_page(**kw)
        return self.html


class _BenchListPlugin(BaseListPlugin):

    def render_page(self, list_view: ListView):
        self.html = ""
        kw = Storage()
        kw.list_view = list_view
        kw.page = 1
        kw.page_url = "?page="
        self.response_page(**kw)
        return self.html


# ----------------------------------------------------------------------
# 计时工具
# ----------------------------------------------------------------------
def bench(scenario: str, n: int, fn, iters: int, warmup: int = 1):
    """对 fn() 计时, 返回统计结果 dict"""
    for _ in range(warmup):
        fn()

    times = []
    for _ in range(iters):
        t0 = time.perf_counter()
        result = fn()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000.0)  # ms

    # 取最后一次的输出体量做参考
    size = len(result) if isinstance(result, (bytes, str)) else 0

    avg = statistics.mean(times)
    return {
        "scenario": scenario,
        "rows": n,
        "iters": iters,
        "avg_ms": avg,
        "min_ms": min(times),
        "max_ms": max(times),
        "median_ms": statistics.median(times),
        "std_ms": statistics.pstdev(times),
        "bytes": size,
        "kb": size / 1024.0,
        "rows_per_sec": n / (avg / 1000.0) if avg > 0 else 0.0,
        # 单线程纯渲染的吞吐上限: QPS = 1000 / median_ms
        # 仅反映「渲染」这一环, 不含路由/鉴权/DB 取数/网络 I/O
        "qps": 1000.0 / statistics.median(times) if statistics.median(times) > 0 else 0.0,
    }


def fmt(v, nd=3):
    return f"{v:.{nd}f}"


def print_scenario_block(title: str, rows):
    print(f"\n=== {title} ===")
    header = (f"{'rows':>8} | {'avg_ms':>10} | {'min_ms':>10} | "
              f"{'max_ms':>10} | {'median_ms':>10} | {'std_ms':>8} | "
              f"{'output_KB':>9} | {'rows/sec':>12} | {'qps':>8}")
    print(header)
    print("-" * len(header))
    for r in rows:
        print(f"{r['rows']:>8} | {fmt(r['avg_ms'],3):>10} | {fmt(r['min_ms'],3):>10} | "
              f"{fmt(r['max_ms'],3):>10} | {fmt(r['median_ms'],3):>10} | "
              f"{fmt(r['std_ms'],3):>8} | {fmt(r['kb'],2):>9} | "
              f"{fmt(r['rows_per_sec'],0):>12} | {fmt(r['qps'],1):>8}")


def write_csv(path: str, all_rows: list):
    import csv
    fields = ["scenario", "rows", "iters", "avg_ms", "min_ms", "max_ms",
              "median_ms", "std_ms", "bytes", "kb", "rows_per_sec", "qps"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in all_rows:
            w.writerow(r)
    print(f"\nCSV 已导出: {path}")


def main():
    parser = argparse.ArgumentParser(description="table_plugin/list_plugin 渲染性能基准")
    parser.add_argument("--rows", default="100,1000,5000,10000",
                        help="行数/条目数, 逗号分隔, 默认 100,1000,5000,10000")
    parser.add_argument("--iters", type=int, default=10, help="每个场景重复次数, 默认 10")
    parser.add_argument("--warmup", type=int, default=1, help="预热次数, 默认 1")
    parser.add_argument("--no-page", action="store_true", help="跳过整页渲染(仅测组件)")
    parser.add_argument("--csv", default="", help="导出 CSV 结果的文件路径")
    args = parser.parse_args()

    row_list = [int(x) for x in args.rows.split(",") if x.strip()]
    iters = max(1, args.iters)
    warmup = max(0, args.warmup)

    print("=" * 64)
    print(" table_plugin / list_plugin 渲染性能基准")
    print(f" 行数档位: {row_list}")
    print(f" 每场景重复: {iters} 次, 预热: {warmup} 次")
    print("=" * 64)

    all_rows = []

    # 1) DataTable 组件渲染
    table_results = []
    for n in row_list:
        table = build_data_table(n)
        res = bench("DataTable.render", n, table.render, iters, warmup)
        table_results.append(res)
        all_rows.append(res)
    print_scenario_block("DataTable.render()  —— table_plugin 核心表格渲染", table_results)

    # 2) ListView 组件渲染
    list_results = []
    for n in row_list:
        lv = build_list_view(n)
        res = bench("ListView.render", n, lv.render, iters, warmup)
        list_results.append(res)
        all_rows.append(res)
    print_scenario_block("ListView.render()  —— list_plugin 核心列表渲染", list_results)

    if not args.no_page:
        # 3) TablePlugin 整页渲染（BaseTablePlugin.response_page）
        tplugin_results = []
        for n in row_list:
            table = build_data_table(n)
            plugin = _BenchTablePlugin()
            res = bench("TablePlugin page", n,
                        lambda: plugin.render_page(table), iters, warmup)
            tplugin_results.append(res)
            all_rows.append(res)
        print_scenario_block("BaseTablePlugin.response_page()  —— 整页(含模板 include)",
                             tplugin_results)

        # 4) ListPlugin 整页渲染（BaseListPlugin.response_page）
        lplugin_results = []
        for n in row_list:
            lv = build_list_view(n)
            plugin = _BenchListPlugin()
            res = bench("ListPlugin page", n,
                        lambda: plugin.render_page(lv), iters, warmup)
            lplugin_results.append(res)
            all_rows.append(res)
        print_scenario_block("BaseListPlugin.response_page()  —— 整页(含模板 include)",
                             lplugin_results)

    # 同量级横向对比
    print("\n=== 同量级对比 (整页渲染 ms / 组件渲染 ms) ===")
    comp = {}
    for r in all_rows:
        comp.setdefault(r["rows"], {})[r["scenario"]] = r
    hdr = (f"{'rows':>8} | {'DataTable':>10} | {'ListView':>10} | "
           f"{'TablePage':>10} | {'ListPage':>10}")
    print(hdr)
    print("-" * len(hdr))
    for n in row_list:
        d = comp.get(n, {})
        dt = d.get("DataTable.render", {})
        lv = d.get("ListView.render", {})
        tp = d.get("TablePlugin page", {})
        lp = d.get("ListPlugin page", {})
        print(f"{n:>8} | "
              f"{fmt(dt.get('avg_ms',0),3):>10} | "
              f"{fmt(lv.get('avg_ms',0),3):>10} | "
              f"{fmt(tp.get('avg_ms',0),3):>10} | "
              f"{fmt(lp.get('avg_ms',0),3):>10}")

    if args.csv:
        write_csv(args.csv, all_rows)

    print("\n完成。")


if __name__ == "__main__":
    main()
