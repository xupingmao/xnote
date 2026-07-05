"""
扫描 xnote_handlers 中的孤立 HTML 模板文件。

检测逻辑：
1. 遍历 xnote_handlers/ 收集所有 .html 文件
2. 在 Python 代码中搜索 xtemplate.render("path") 等引用
3. 在 HTML 模板中搜索 {% extends "path" %} / {% include "path" %} 等引用
4. 处理模板引擎的隐式解析规则（"base" -> "common/base.html" 等）
5. 输出完全未被引用的模板文件
"""
import os
import re
import sys
import time
from typing import List
from datetime import datetime
from xutils import fsutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDLERS_DIR = os.path.join(PROJECT_ROOT, "xnote_handlers")
XNOTE_DIR = os.path.join(PROJECT_ROOT, "xnote")
XUTILS_DIR = os.path.join(PROJECT_ROOT, "xutils")
EXT_HANDLERS_DIR = "./ext_handlers"
PLUGINS_DIR = ""  # 运行时动态确定，扫描时忽略（测试环境有 test_plugin.html）

# 模板引擎内置的隐式解析规则
SHORTCUT_MAP = {
    "base": "common/base.html",
    "wide_base": "common/wide_base.html",
}

# 路径映射（默认值）
PATH_MAPPING = {
    "$base_nav_left": "common/nav/base_nav_left.html",
    "$base_nav_top": "common/nav/base_nav_top.html",
}

# 正则：Python 中的模板渲染调用
# 匹配 xtemplate.render("path") / render("path") / render_by_ua("path")
RE_PYTHON_RENDER = re.compile(
    r'(?:xtemplate\.)?render(?:_by_ua|_text)?\s*\(\s*'
    r'(?P<quote>["\'])(?P<path>[^"\']+?)(?P=quote)',
)

# 正则：动态模板路径赋值
# template_name = "path" / template_file = "path" / template = "path"
# self.template_name = "path" / self.template_path = "path"
# kw.template_name = "path" / kw.template = "path"
# base_template_path = "path" / html_template_path = "path"
RE_PYTHON_TEMPLATE_ASSIGN = re.compile(
    r'(?:template(?:_name|_file|_path)?|base_template_path|html_template_path)'
    r'\s*=\s*'
    r'(?P<quote>["\'])(?P<path>[^"\']+?\.html)(?P=quote)',
)

# 正则：return "path.html" 模式（如 plugin_page.py 的 return "plugin/page/plugins_v1.html"）
RE_PYTHON_RETURN_HTML = re.compile(
    r'return\s+'
    r'(?P<quote>["\'])(?P<path>[^"\']+?\.html)(?P=quote)',
)

# 正则：HTML 中的 extends/include
RE_EXTENDS = re.compile(
    r'\{%\s+extends\s+["\']?(?P<path>[^"\'\s%}]+)["\']?\s*%\}',
)
RE_INCLUDE = re.compile(
    r'\{%\s+include\s+["\']?(?P<path>[^"\'\s%}]+)["\']?\s*%\}',
)

# 注意：{% extends base %} 里 "base" 不是字面路径，它是变量名，
# 但模板引擎会将变量名作为字符串直接 resolve，所以我们一视同仁提取即可。

# 已知的特殊模板配置（在 xtemplate.py 中硬编码）
KNOWN_ADDITIONAL_REFS = [
    "plugin/base/base_plugin.html",
    "plugin/base/base_form_plugin.html",
]


def is_in_test_or_virtual(path):
    """跳过测试目录中的模板"""
    return "tests" in path.split(os.sep)


def collect_html_files(root_dir: str):
    """收集所有 .html 文件（含 .mobile.html）"""
    files = {}
    for dirpath, _, filenames in os.walk(root_dir):
        for fn in filenames:
            if fn.endswith(".html"):
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, root_dir).replace("\\", "/")
                st = os.stat(full)
                files[rel] = {
                    "path": full,
                    "size": st.st_size,
                    "mtime": datetime.fromtimestamp(st.st_mtime),
                }
    return files


def _extract_from_patterns(content: str, patterns: List[re.Pattern]):
    """用多个 regex 从内容中提取模板路径"""
    refs = set()
    for pattern in patterns:
        for m in pattern.finditer(content):
            path = m.group("path")
            # 排除非模板路径的误匹配
            if " " in path or "\t" in path:
                continue
            refs.add(path)
    return refs


def collect_python_references(scan_dirs):
    """从 Python 文件中收集模板引用"""
    patterns = [RE_PYTHON_RENDER, RE_PYTHON_TEMPLATE_ASSIGN, RE_PYTHON_RETURN_HTML, RE_INCLUDE, RE_EXTENDS]
    refs = set()
    for root_dir in scan_dirs:
        if not os.path.isdir(root_dir):
            continue
        for dirpath, _, filenames in os.walk(root_dir):
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                fpath = os.path.join(dirpath, fn)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    continue
                refs |= _extract_from_patterns(content, patterns)
    return refs


def collect_html_references(root_dir: str):
    """从 HTML 模板文件中收集 {% extends %} / {% include %} 引用"""
    patterns = [RE_EXTENDS, RE_INCLUDE]
    refs = set()
    for dirpath, _, filenames in os.walk(root_dir):
        for fn in filenames:
            if not fn.endswith(".html"):
                continue
            fpath = os.path.join(dirpath, fn)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            refs |= _extract_from_patterns(content, patterns)
    return refs


def resolve_reference(ref: str):
    """将引用名称转换为相对于 HANDLERS_DIR 的路径"""
    # 别名
    if ref in SHORTCUT_MAP:
        return SHORTCUT_MAP[ref]

    # 路径映射变量
    if ref in PATH_MAPPING:
        return PATH_MAPPING[ref]

    # $ext/ $plugin/ 前缀 — 不在 xnote_handlers 下，忽略
    if ref.startswith("$ext/") or ref.startswith("$plugin/"):
        return None

    # 已经是相对路径
    if ref.endswith(".html"):
        return ref

    return ref


def resolve_reference_set(refs):
    """将引用集合解析为最终路径集合"""
    resolved = set()
    for ref in refs:
        r = resolve_reference(ref)
        if r is not None:
            resolved.add(r)
    return resolved


def main():
    if not os.path.isdir(HANDLERS_DIR):
        print(f"错误：找不到 {HANDLERS_DIR}")
        sys.exit(1)

    print(f"扫描目录: {HANDLERS_DIR}\n")

    # 1. 收集所有 .html 文件
    all_files = collect_html_files(HANDLERS_DIR)
    print(f"共发现 {len(all_files)} 个 .html 模板文件")

    # 2. 从 Python 代码中收集引用（扫描 xnote_handlers, xnote, xutils）
    py_refs = collect_python_references([HANDLERS_DIR, XNOTE_DIR, XUTILS_DIR])
    print(f"Python 代码引用数: {len(py_refs)}")

    # 3. 从 HTML 模板中收集引用
    html_refs = collect_html_references(HANDLERS_DIR)
    print(f"HTML 模板引用数: {len(html_refs)}")

    # 4. 合并已知的特殊引用
    all_refs = py_refs | html_refs | set(KNOWN_ADDITIONAL_REFS)
    resolved_refs = resolve_reference_set(all_refs)

    print(f"去重并解析后的引用数: {len(resolved_refs)}\n")

    # 5. 检测自引用：排除自身对自己的 extends/include
    # 实际上自引用的场景极少，并且 resolved_refs 包含了模板文件自身的路径，
    # 但模板不会 extends/include 自己，所以问题不大。

    # 6. 找孤立文件
    orphans = []
    for rel_path in sorted(all_files.keys()):
        if rel_path.startswith("tools/"):
            continue
        
        if rel_path not in resolved_refs:
            info = all_files[rel_path]
            orphans.append((rel_path, info["size"], info["mtime"]))

    # 7. 输出
    if not orphans:
        print("没有发现孤立的模板文件!")
        return

    print(f"发现 {len(orphans)} 个孤立的模板文件:\n")
    print(f"{'模板路径':<60} {'大小':>8} {'修改时间'}")
    print("-" * 100)
    for path, size, mtime in sorted(orphans, key=lambda x: x[0]):
        size_str = f"{size} B" if size < 1024 else f"{size/1024:.1f} KB"
        time_str = mtime.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{path:<60} {size_str:>8}  {time_str}")

    # 8. 额外提示：没有被解析的动态引用
    dynamic_refs = []
    for ref in sorted(all_refs):
        r = resolve_reference(ref)
        if r is None:
            dynamic_refs.append(ref)
    if dynamic_refs:
        print(f"\n以下 {len(dynamic_refs)} 个引用指向外部目录（$ext/$plugin），未计入扫描:")
        for ref in dynamic_refs:
            print(f"  - {ref}")

    # 建议
    if orphans:
        print(f"\n提示：这些文件可能已被废弃，确认无引用后可安全删除。")


if __name__ == "__main__":
    main()
