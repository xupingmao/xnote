"""
扫描并清理未使用的 CSS 类。

工作流程:
1. 解析 CSS 文件, 提取每条规则的「主体类」和「引用类」
   - 主体类: 选择器真正作用在哪些 class 上 (决定这条规则还有没有元素能匹配)
   - 引用类: :not()/:is()/:has() 内部提到的 class (只是引用, 不代表归属)
2. 扫描源码目录 (HTML 模板 / Python / JS), 抽取所有标识符
3. 判定: 主体类在源码里找不到 -> 该规则没有元素能匹配 -> 可删除
4. 默认只输出报告, 加 --apply 才真正改写 CSS 文件 (自动备份 .bak)

注意:
- :not(.x) 中 x 未被使用时选择器恒成立, 这类规则会**保留**, 不误删
- 判定时会排除 CSS 文件自身的文本, 避免「自己引用自己」的循环论证
- 动态拼接的类名可能被误判, 请用 --whitelist 兜底

用法:
    python scripts/scan-unused-css.py                    # 只读报告
    python scripts/scan-unused-css.py --stats            # 只看按文件汇总
    python scripts/scan-unused-css.py --apply            # 真正删除 (备份 .bak)
    python scripts/scan-unused-css.py --css-file _static/css/note.css
    python scripts/scan-unused-css.py --scan-dir xnote_handlers --scan-dir xnote
    python scripts/scan-unused-css.py --json report.json --max-show 0
"""
import os
import re
import json
import argparse
from typing import List, Set, Dict, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 默认分析的 CSS 目录
DEFAULT_CSS_DIRS = [
    "_static/css",
]

# 默认扫描的源码目录
DEFAULT_SCAN_DIRS = [
    "xnote",
    "xnote_handlers",
    "xutils",
    "scripts",
]

# CSS 侧默认忽略 (第三方库 / 构建产物)
DEFAULT_CSS_EXCLUDES = [
    "**/lib/**",
    "**/*.min.css",
    "**/app.build.css",
]

# 源码侧默认忽略
DEFAULT_SCAN_EXCLUDES = [
    "**/.git/**",
    "**/node_modules/**",
    "**/__pycache__/**",
    "**/testdata/**",
    "**/data/**",
    "**/dist/**",
    "**/tmp/**",
    "**/htmlcov/**",
    "**/tests/**",
]

SOURCE_EXTENSIONS = {
    ".html", ".htm", ".py", ".js", ".jsx", ".ts", ".vue", ".md",
    ".txt", ".yml", ".json",
}

# CSS 类名 (字母数字下划线中划线 + 中文)
RE_CSS_CLASS = re.compile(r"\.([-\w一-鿿]+)")
# 函数型伪类, 内部的 class 属于「引用」
RE_PSEUDO_FUNC = re.compile(r":(?:not|is|has|matches|where)\(([^)]*)\)")
# 属性选择器
RE_ATTR_SELECTOR = re.compile(r"\[[^\]]*\]")
# 伪类 / 伪元素
RE_PSEUDO = re.compile(r"::?[a-zA-Z][\w-]*(?:\([^)]*\))?")
# CSS 注释
RE_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
# 源码中的标识符 ([-\w]+ 覆盖 btn-primary 这种带连字符的类名)
RE_SOURCE_TOKEN = re.compile(r"[-\w一-鿿]+")
# 数字后缀系列类: level-1 / col-md-4 / mb-2
RE_SERIES_CLASS = re.compile(r"^(.*?)-(\d+)$")

# 源码里显式的 class 赋值写法
RE_CLASS_ATTR_ASSIGN = re.compile(
    r"""(?:className|css_class|addClass|add_class|removeClass|remove_class"""
    r"""|toggleClass|toggle_class|hasClass|has_class|set_class)\s*[=:(]\s*"""
    r"""["'](?P<value>[^"'{}]+)["']"""
)
RE_CLASS_ATTR_HTML = re.compile(
    r"""class\s*=\s*(?P<q>["'])(?P<value>.*?)(?P=q)""", re.S
)
RE_CLASSLIST = re.compile(
    r"""classList\s*\.\s*(?:add|remove|toggle|contains)\s*\(\s*["'](?P<value>[^"']+)["']"""
)

# 需要跳过的 at-rule (其内部的选择器不是普通规则)
SKIP_AT_RULES = ("keyframes", "-webkit-keyframes", "-moz-keyframes", "font-face",
                 "page", "counter-style", "property")


def _glob_to_regex(pattern: str) -> "re.Pattern":
    """把简化的 glob 转成正则: `**` 跨目录, `*` 不跨目录, `?` 单字符"""
    result = []
    index = 0
    while index < len(pattern):
        ch = pattern[index]
        if ch == "*":
            if pattern[index:index + 2] == "**":
                result.append(".*")
                index += 2
                continue
            result.append("[^/]*")
        elif ch == "?":
            result.append("[^/]")
        else:
            result.append(re.escape(ch))
        index += 1
    return re.compile("^" + "".join(result) + "$")


def match_exclude(rel_path: str, patterns: List[str]) -> bool:
    """路径模式匹配: 支持 `**/xxx/**`、`*.css`、精确匹配"""
    norm = rel_path.replace("\\", "/")
    for pattern in patterns:
        p = pattern.replace("\\", "/").lstrip("./")
        if "*" in p or "?" in p:
            if _glob_to_regex(p).match(norm):
                return True
        elif p == norm or norm.startswith(p + "/"):
            return True
    return False


def strip_css_comments(content: str) -> str:
    """去掉注释但保持字符串长度不变, 保证偏移量与原文对齐"""
    return RE_CSS_COMMENT.sub(lambda m: " " * len(m.group(0)), content)


def find_string_ranges(content: str) -> List[Tuple[int, int]]:
    """找出 CSS 中字符串字面量的区间"""
    ranges = []
    quote = ""
    start = -1
    index = 0
    escaped = False
    while index < len(content):
        ch = content[index]
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
        elif quote:
            if ch == quote:
                ranges.append((start, index + 1))
                quote = ""
        elif ch in ("'", '"'):
            quote = ch
            start = index
        index += 1
    if quote:
        ranges.append((start, len(content)))
    return ranges


def in_ranges(pos: int, ranges: List[Tuple[int, int]]) -> bool:
    for start, end in ranges:
        if start <= pos < end:
            return True
    return False


def analyze_selector(selector: str) -> Tuple[Set[str], Set[str]]:
    """拆分一个选择器片段 -> (主体类, 引用类)"""
    referenced: Set[str] = set()
    for m in RE_PSEUDO_FUNC.finditer(selector):
        referenced |= set(RE_CSS_CLASS.findall(m.group(1)))

    cleaned = RE_ATTR_SELECTOR.sub(" ", selector)
    cleaned = RE_PSEUDO.sub(" ", cleaned)
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)
    owned = set(RE_CSS_CLASS.findall(cleaned)) - referenced
    return owned, referenced


class SelectorPart:
    """选择器组中的一个成员, 保留其在原始选择器文本中的区间"""

    def __init__(self, text: str, start: int, end: int):
        self.text = text
        self.start = start
        self.end = end
        self.owned, self.referenced = analyze_selector(text)


def split_selector_group(selector: str) -> List[SelectorPart]:
    """按顶层逗号切分选择器组 ('a, b > c' -> ['a', 'b > c'])

    注意: 切分时跳过属性选择器和括号内部, 但返回的文本必须保留原文
    (含 [attr]/伪类), 这样后续重写选择器时不会丢失内容。
    """
    masked = RE_ATTR_SELECTOR.sub(lambda m: " " * len(m.group(0)), selector)
    bounds: List[Tuple[int, int]] = []
    depth = 0
    start = 0
    for index, ch in enumerate(masked):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            bounds.append((start, index))
            start = index + 1
    bounds.append((start, len(selector)))

    parts = []
    for begin, finish in bounds:
        text = selector[begin:finish].strip()
        if not text:
            continue
        # 重新定位 strip 之后的真实起止
        raw = selector[begin:finish]
        leading = len(raw) - len(raw.lstrip())
        parts.append(SelectorPart(text, begin + leading,
                                  begin + leading + len(text)))
    return parts


class CssRule:
    """一条 CSS 规则: 选择器 + 声明块"""

    def __init__(self, selector_text: str, selector_start: int, block_start: int,
                 block_end: int, line: int):
        self.selector_text = selector_text
        self.selector_start = selector_start
        self.block_start = block_start
        self.block_end = block_end  # 指向匹配的 '}'
        self.line = line
        self.parts = split_selector_group(selector_text)

    def owned_class_set(self) -> Set[str]:
        result: Set[str] = set()
        for part in self.parts:
            result |= part.owned
        return result

    def droppable_indexes(self, unused_classes: Set[str]) -> List[int]:
        """返回可以剔除的选择器成员下标"""
        result = []
        for index, part in enumerate(self.parts):
            if not part.owned:
                continue  # 纯标签/属性选择器, 不动
            if not part.owned <= unused_classes:
                continue  # 还有类在用
            if part.referenced & unused_classes:
                # :not(.x) 引用了未使用的类 -> 选择器恒成立, 规则仍然有效
                continue
            result.append(index)
        return result

    def build_selector(self, droppable: List[int]) -> str:
        """剔除指定成员后重组选择器文本"""
        dropped = set(droppable)
        kept = [part.text for i, part in enumerate(self.parts)
                if i not in dropped]
        return ", ".join(kept)


def parse_css(content: str) -> List[CssRule]:
    """解析 CSS 文本, 提取所有规则及其在原文件中的偏移量"""
    text = strip_css_comments(content)
    str_ranges = find_string_ranges(text)
    rules: List[CssRule] = []
    skip_ends: List[int] = []  # @keyframes 等需要跳过的区间右端点

    index = 0
    length = len(text)
    buf: List[str] = []
    selector_start = 0

    while index < length:
        while skip_ends and index > skip_ends[-1]:
            skip_ends.pop()

        ch = text[index]

        if skip_ends:
            index += 1
            continue

        if ch == "{":
            selector_text = "".join(buf).strip()
            # 找到匹配的 '}'
            depth = 1
            cursor = index + 1
            while cursor < length:
                if in_ranges(cursor, str_ranges):
                    cursor += 1
                    continue
                if text[cursor] == "{":
                    depth += 1
                elif text[cursor] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                cursor += 1
            block_end = cursor

            if selector_text.startswith("@"):
                name = selector_text[1:].strip().split()[0].split("(")[0]
                if name in SKIP_AT_RULES:
                    skip_ends.append(block_end)
                    buf = []
                    index = block_end + 1
                    selector_start = index
                    continue
                # @media 等容器: 跨过 '{' 继续解析内部规则
                buf = []
                index += 1
                selector_start = index
                continue

            if selector_text:
                # selector_text 经过 strip, 偏移量需要同步前移
                raw_selector = "".join(buf)
                leading = len(raw_selector) - len(raw_selector.lstrip())
                real_start = selector_start + leading
                line = text.count("\n", 0, real_start) + 1
                rules.append(CssRule(selector_text, real_start, index,
                                     block_end, line))

            buf = []
            index = block_end + 1
            selector_start = index
            continue

        if ch == ";" and "".join(buf).strip().startswith("@"):
            # 顶层的 @import/@charset
            buf = []
            index += 1
            selector_start = index
            continue

        buf.append(ch)
        index += 1

    return rules


def collect_css_files(css_dirs: List[str], css_files: List[str],
                      excludes: List[str]) -> List[str]:
    result: Set[str] = set()
    for item in css_dirs:
        abs_path = os.path.join(PROJECT_ROOT, item)
        if os.path.isfile(abs_path):
            result.add(item)
            continue
        if not os.path.isdir(abs_path):
            print(f"警告: CSS 路径不存在, 已跳过 -> {item}")
            continue
        for dirpath, _, filenames in os.walk(abs_path):
            for fn in filenames:
                if not fn.endswith(".css"):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, PROJECT_ROOT).replace("\\", "/")
                if match_exclude(rel, excludes):
                    continue
                result.add(rel)
    for item in css_files:
        rel = item.replace("\\", "/")
        if match_exclude(rel, excludes):
            continue
        result.add(rel)
    return sorted(result)


def collect_source_files(scan_dirs: List[str], excludes: List[str]) -> List[str]:
    result: Set[str] = set()
    for item in scan_dirs:
        abs_path = os.path.join(PROJECT_ROOT, item)
        if os.path.isfile(abs_path):
            result.add(item)
            continue
        if not os.path.isdir(abs_path):
            print(f"警告: 源码路径不存在, 已跳过 -> {item}")
            continue
        for dirpath, _, filenames in os.walk(abs_path):
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in SOURCE_EXTENSIONS:
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, PROJECT_ROOT).replace("\\", "/")
                if match_exclude(rel, excludes):
                    continue
                result.add(rel)
    return sorted(result)


def read_text(rel_or_abs: str) -> str:
    full = rel_or_abs if os.path.isabs(rel_or_abs) \
        else os.path.join(PROJECT_ROOT, rel_or_abs)
    for encoding in ("utf-8", "gbk", "latin-1"):
        try:
            # newline="": 保留原始换行风格, 避免 CRLF 文件被写成 LF
            with open(full, "r", encoding=encoding, newline="") as fp:
                return fp.read()
        except UnicodeDecodeError:
            continue
        except OSError as e:
            print(f"警告: 读取失败 {rel_or_abs}: {e}")
            return ""
    return ""


def extract_tokens(content: str) -> Set[str]:
    """抽取源码中的所有标识符

    含连字符的 token 会额外拆分出所有连续子串 ('x-a-b' -> 'x','a','b','x-a','a-b',
    'x-a-b'), 这样 foo-bar 作为完整类名的同时也允许从拼接串里被匹配到。
    """
    tokens: Set[str] = set()
    for m in RE_SOURCE_TOKEN.finditer(content):
        token = m.group(0).strip("-")
        if not token:
            continue
        tokens.add(token)
        if "-" in token:
            parts = token.split("-")
            if len(parts) > 8:  # 防御随机长串产生的组合爆炸
                continue
            for i in range(len(parts)):
                for j in range(i + 1, len(parts) + 1):
                    tokens.add("-".join(parts[i:j]))
    return tokens


def build_source_index(source_files: List[str]) -> Set[str]:
    """构建源码侧的词表"""
    tokens: Set[str] = set()
    for rel in source_files:
        content = read_text(rel)
        if not content:
            continue
        tokens |= extract_tokens(content)
        # 显式 class 属性值里的模板变量 ({{ xxx }}) 剥掉后再收一次
        for pattern in (RE_CLASS_ATTR_ASSIGN, RE_CLASS_ATTR_HTML, RE_CLASSLIST):
            for m in pattern.finditer(content):
                value = m.group("value")
                value = re.sub(r"\{\{.*?\}\}", " ", value, flags=re.S)
                for token in re.split(r"[\s+]+", value):
                    token = token.strip()
                    if token:
                        tokens.add(token)
    return tokens


def check_balanced(content: str) -> bool:
    """检查删除后 CSS 的大括号是否仍然平衡 (字符串内的括号不计)"""
    ranges = find_string_ranges(content)
    depth = 0
    for index, ch in enumerate(content):
        if in_ranges(index, ranges):
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def drop_empty_at_rules(content: str) -> str:
    """清理由删除产生的空 at-rule 块 (@media ... { })"""
    pattern = re.compile(r"@[a-zA-Z-]+[^{;]*?\{[ \t\r\n]*\}[ \t]*(?:\r\n|\r|\n)?")
    previous = None
    while previous != content:
        previous = content
        content = pattern.sub("", content)
    return content


def collapse_blank_lines(content: str) -> str:
    """整理删除后多余空行, 保留原始的换行符风格"""
    def repl(m: "re.Match"):
        head = re.match(r"\r\n|\r|\n", m.group(0))
        return head.group(0) * 2 if head else m.group(0)
    return re.sub(r"(?:\r\n|\r|\n)(?:[ \t]*(?:\r\n|\r|\n)){2,}", repl, content)


def normalize_newlines(content: str, reference: str) -> str:
    """按原文件的换行风格归一化

    源文件是纯 CRLF / 纯 LF 时强制转换回去, 避免整份 diff;
    混合换行则保持原样。
    """
    crlf = reference.count("\r\n")
    total_lf = reference.count("\n")
    if crlf == 0:
        target = "\n"
    elif crlf == total_lf:
        target = "\r\n"
    else:
        return content  # 混合换行, 不做全局转换
    flat = content.replace("\r\n", "\n").replace("\r", "\n")
    return flat.replace("\n", target)


def apply_removal(rel_path: str, removals: List[Tuple[CssRule, List[int]]],
                  backup: bool = True, dry_run: bool = True) -> int:
    """从 CSS 文件中删除规则

    removals: [(rule, droppable_indexes)]
      - 下标覆盖 rule 的全部成员 -> 删除整条规则
      - 否则 -> 重写选择器文本, 去掉失效的成员
    返回删除的整规则数量; 结构校验不通过时返回 -1 且不写文件
    """
    full = os.path.join(PROJECT_ROOT, rel_path)
    with open(full, "r", encoding="utf-8", newline="") as fp:
        content = fp.read()

    # 所有编辑都基于原始 content 的坐标, 统一倒序应用
    edits: List[Tuple[int, int, str]] = []

    for rule, droppable in removals:
        if len(droppable) < len(rule.parts):
            new_text = rule.build_selector(droppable)
            edits.append((rule.selector_start,
                          rule.selector_start + len(rule.selector_text),
                          new_text))
            continue
        start = rule.selector_start
        while start > 0 and content[start - 1] in " \t":
            start -= 1
        if start > 0 and content[start - 1] == "\n":
            start -= 1
        edits.append((start, rule.block_end + 1, ""))

    if dry_run:
        return sum(1 for _, _, text in edits if not text)

    new_content = content
    for start, end, text in sorted(edits, key=lambda x: x[0], reverse=True):
        new_content = new_content[:start] + text + new_content[end:]

    new_content = drop_empty_at_rules(new_content)
    # 整理删除产生的多余空行, 再还原原有换行风格
    new_content = collapse_blank_lines(new_content)
    new_content = normalize_newlines(new_content, content)

    if not check_balanced(new_content):
        print(f"  [跳过] {rel_path}: 删除后大括号不平衡, 已放弃写入")
        return -1

    if backup:
        with open(full + ".bak", "w", encoding="utf-8", newline="") as fp:
            fp.write(content)

    with open(full, "w", encoding="utf-8", newline="") as fp:
        fp.write(new_content)

    return sum(1 for _, _, text in edits if not text)


def load_whitelist(path: str) -> Set[str]:
    result: Set[str] = set()
    full = path if os.path.isabs(path) else os.path.join(PROJECT_ROOT, path)
    if not os.path.isfile(full):
        print(f"警告: 白名单文件不存在 -> {path}")
        return result
    with open(full, "r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if line and not line.startswith("#"):
                result.add(line.lstrip("."))
    return result


def series_key(class_name: str) -> str:
    """系列类的分组键: 'level-3' -> 'level-'; 非系列返回空串"""
    m = RE_SERIES_CLASS.match(class_name)
    if m:
        return m.group(1) + "-"
    return ""


def find_protected_series(defined_classes: Dict[str, Set[str]],
                          raw_unused: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """找出需要保护的类

    形如 level-1/level-2/... 的系列类通常由代码动态拼接 (`f"level-{n}"`),
    只要系列里还有成员在用, 其余成员就保守保留, 避免误删。
    """
    protected: Dict[str, Set[str]] = {rel: set() for rel in raw_unused}

    group_members: Dict[str, Set[str]] = {}
    for classes in defined_classes.values():
        for cls in classes:
            key = series_key(cls)
            if key:
                group_members.setdefault(key, set()).add(cls)

    if not group_members:
        return protected

    for key, members in group_members.items():
        alive = [c for c in members
                 if all(c not in raw_unused.get(rel, set())
                        for rel in raw_unused)]
        if not alive:
            continue
        # 系列仍有成员在用 -> 未使用的同族成员一律保留
        for rel, unused in raw_unused.items():
            for cls in unused:
                if series_key(cls) == key:
                    protected[rel].add(cls)
    return protected


def write_json(data, output_path):
    if not output_path:
        return
    full = output_path if os.path.isabs(output_path) \
        else os.path.join(PROJECT_ROOT, output_path)
    try:
        with open(full, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        print(f"JSON 报告已写入: {output_path}")
    except OSError as e:
        print(f"写入 JSON 失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="扫描并清理未使用的 CSS 类")
    parser.add_argument("--css-dir", action="append", default=None,
                        help="CSS 目录/文件, 可多次指定 (默认 _static/css)")
    parser.add_argument("--css-file", action="append", default=None,
                        help="额外指定的单个 CSS 文件")
    parser.add_argument("--scan-dir", action="append", default=None,
                        help="源码目录, 可多次指定")
    parser.add_argument("--exclude", action="append", default=None,
                        help="额外排除的路径模式, 如 '**/vendor/**'")
    parser.add_argument("--whitelist", default=None,
                        help="白名单文件, 每行一个类名, # 开头为注释")
    parser.add_argument("--include-lib", action="store_true",
                        help="同时分析第三方库 CSS (_static/lib)")
    parser.add_argument("--keep-series", action="store_true", default=True,
                        help="保留疑似动态拼接的系列类 (默认开启)")
    parser.add_argument("--no-keep-series", dest="keep_series",
                        action="store_false",
                        help="关闭系列类保护, 让 col-md-N 之类也参与删除")
    parser.add_argument("--apply", action="store_true",
                        help="真正删除 CSS 规则 (默认只报告)")
    parser.add_argument("--no-backup", action="store_true",
                        help="--apply 时不生成 .bak 备份")
    parser.add_argument("-y", "--yes", action="store_true",
                        help="允许多文件批量删除 (默认超过 1 个文件会中止)")
    parser.add_argument("--stats", action="store_true",
                        help="只输出每个 CSS 文件的汇总统计")
    parser.add_argument("--json", dest="json_output", default=None,
                        help="将结果写入 JSON 文件")
    parser.add_argument("--max-show", type=int, default=100,
                        help="最多展示多少条明细 (默认 100, 0 表示不限)")
    args = parser.parse_args()

    css_files_arg = [p.replace("\\", "/") for p in (args.css_file or [])]
    if args.css_dir:
        css_dirs = args.css_dir
    elif css_files_arg:
        css_dirs = []  # 只显式指定了文件时, 不再扫描默认目录
    else:
        css_dirs = DEFAULT_CSS_DIRS
    css_excludes = list(DEFAULT_CSS_EXCLUDES)
    scan_excludes = list(DEFAULT_SCAN_EXCLUDES) + (args.exclude or [])

    if args.include_lib:
        css_excludes = [p for p in css_excludes if "lib" not in p]
        css_dirs = css_dirs + ["_static/lib"]

    scan_dirs = args.scan_dir or DEFAULT_SCAN_DIRS

    css_files = collect_css_files(css_dirs, css_files_arg, css_excludes)
    if not css_files:
        print("没有找到任何 CSS 文件")
        return

    source_files = collect_source_files(scan_dirs, scan_excludes)
    if not source_files:
        print("没有找到任何源码文件, 无法判断使用情况")
        return

    whitelist = load_whitelist(args.whitelist) if args.whitelist else set()

    print("=" * 78)
    print("CSS 未使用类扫描")
    print("=" * 78)
    print(f"CSS 文件 : {len(css_files)} 个")
    print(f"源码文件 : {len(source_files)} 个")
    print(f"模式     : {'删除 (--apply)' if args.apply else '只读报告'}")
    print("")

    source_tokens = build_source_index(source_files)
    print(f"源码词表 : {len(source_tokens)} 个 token")

    # 各 CSS 文件的词表, 用于跨 CSS 引用判断 (排除自引用)
    css_tokens: Dict[str, Set[str]] = {}
    css_rules: Dict[str, List[CssRule]] = {}
    css_contents: Dict[str, str] = {}
    for rel in css_files:
        content = read_text(rel)
        if not content:
            continue
        css_contents[rel] = content
        css_tokens[rel] = extract_tokens(content)
        css_rules[rel] = parse_css(content)

    def is_used(class_name: str, self_file: str) -> bool:
        if class_name in source_tokens:
            return True
        for rel, tokens in css_tokens.items():
            if rel == self_file:
                continue
            if class_name in tokens:
                return True
        return False

    # 1) 收集每个 CSS 文件定义的类及其首次出现的行号
    defined_lines: Dict[str, Dict[str, int]] = {}
    defined_all: Dict[str, Set[str]] = {}
    for rel in css_files:
        rules = css_rules.get(rel, [])
        lines: Dict[str, int] = {}
        for rule in rules:
            for cls in rule.owned_class_set():
                lines.setdefault(cls, rule.line)
        defined_lines[rel] = lines
        defined_all[rel] = set(lines)

    # 2) 计算原始未使用集合
    raw_unused: Dict[str, Set[str]] = {}
    for rel in css_files:
        unused: Set[str] = set()
        for cls in defined_all[rel]:
            if cls in whitelist:
                continue
            if not is_used(cls, rel):
                unused.add(cls)
        raw_unused[rel] = unused

    # 3) 动态拼接系列类保护
    if args.keep_series:
        protected = find_protected_series(defined_all, raw_unused)
    else:
        protected = {rel: set() for rel in css_files}

    n_protected = sum(len(v) for v in protected.values())
    if n_protected:
        print(f"系列保护 : {n_protected} 个疑似动态拼接的类已保留"
              f" (用 --no-keep-series 关闭)")

    # 4) 生成删除计划 (先看有多少文件会被改动, 避免误伤整个项目)
    plans: Dict[str, List[Tuple[CssRule, List[int]]]] = {}
    for rel in css_files:
        if not defined_lines[rel]:
            continue
        removals = []
        for rule in css_rules.get(rel, []):
            droppable = rule.droppable_indexes(raw_unused[rel] - protected[rel])
            if droppable:
                removals.append((rule, droppable))
        if removals:
            plans[rel] = removals

    skipped_build = [rel for rel in plans if rel.endswith("app.build.css")]
    targets = [rel for rel in plans if rel not in skipped_build]

    if skipped_build:
        print(f"跳过构建产物: {', '.join(skipped_build)}")

    if args.apply and len(targets) > 1 and not args.yes:
        print("")
        print("=" * 78)
        print(f"已中止: 本次将修改 {len(targets)} 个 CSS 文件, 属于批量改动。")
        print("请先用 --css-file 单个文件试跑确认效果, 确认无误后加 -y/--yes 再执行:")
        for rel in targets[:10]:
            print(f"    python scripts/scan-unused-css.py --css-file {rel} --apply")
        if len(targets) > 10:
            print(f"    ... 共 {len(targets)} 个")
        print("=" * 78)
        return

    total_classes = 0
    total_unused = 0
    total_removed = 0
    json_data = []

    for rel in css_files:
        defined_classes = defined_lines[rel]
        if not defined_classes:
            continue

        unused_classes = raw_unused[rel] - protected[rel]
        removals = plans.get(rel, [])

        removed = 0
        if removals:
            removed = apply_removal(rel, removals,
                                    backup=not args.no_backup,
                                    dry_run=not args.apply)
            if removed < 0:  # 结构校验失败, 已放弃写入
                removed = 0

        total_classes += len(defined_classes)
        total_unused += len(unused_classes)
        total_removed += removed

        json_data.append({
            "file": rel,
            "total_classes": len(defined_classes),
            "rules_removed": removed,
            "unused_classes": sorted(unused_classes),
            "unused_detail": [
                {"class": c, "line": defined_classes[c]}
                for c in sorted(unused_classes)
            ],
            "skipped_classes": sorted(raw_unused[rel] & protected[rel]),
        })

    print("")
    print(f"{'CSS 文件':<46}{'类总数':>7}{'未使用':>7}{'可删规则':>9}")
    print("-" * 78)
    for entry in sorted(json_data, key=lambda x: -len(x["unused_classes"])):
        if len(entry["unused_classes"]) == 0 and not args.stats:
            continue
        print(f"{entry['file']:<46}{entry['total_classes']:>7}"
              f"{len(entry['unused_classes']):>7}{entry['rules_removed']:>9}")
    print("-" * 78)
    print(f"{'合计':<46}{total_classes:>7}{total_unused:>7}{total_removed:>9}")
    print("")

    write_json(json_data, args.json_output)

    if args.stats:
        return

    shown = 0
    for entry in sorted(json_data, key=lambda x: -len(x["unused_classes"])):
        if not entry["unused_classes"]:
            continue
        print(f"[{entry['file']}]  未使用 {len(entry['unused_classes'])}"
              f" / 共 {entry['total_classes']}")
        for item in entry["unused_detail"]:
            if args.max_show > 0 and shown >= args.max_show:
                print(f"    ... 已达 --max-show={args.max_show} 上限, 调大查看全部")
                break
            print(f"    L{item['line']:<5} .{item['class']}")
            shown += 1
        else:
            print("")
            continue
        break

    if not args.apply and total_unused > 0:
        print("")
        print("提示:")
        print("  1. 动态拼接的类名可能被误判, 删除前建议抽查几项")
        print("  2. 确认无误后加 --apply 执行删除 (默认生成 .bak 备份)")
        print("  3. 需要保留的类写入白名单文件, 用 --whitelist 指定")
    elif args.apply:
        print(f"已清理 {total_removed} 条规则, 备份文件: *.bak")


if __name__ == "__main__":
    main()
