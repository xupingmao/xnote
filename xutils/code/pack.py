# encoding=utf-8
import os
import re
from typing import List, Optional, Tuple
from xutils import fsutil


class CommentFilter:
    """逐行过滤注释(内部使用)

    跨行维护字符串字面量的状态, 避免把字符串里的 # 号当成注释删掉
    """

    # 编码声明, 例如 `# encoding=utf-8` / `# -*- coding: utf-8 -*-`
    ENCODING_RE = re.compile(r"#.*(?:coding|encoding)\s*[:=]")

    def __init__(self, skip_comment=True):
        self.skip_comment = skip_comment
        self._quote = ""
        self._escaped = False

    def handle(self, line: str) -> Optional[str]:
        """处理一行代码, 返回 None 表示整行都是注释、可以丢弃"""
        if not self.skip_comment:
            return line

        tail_start = len(line.rstrip())
        tail = line[tail_start:]  # 行尾的空白字符(包含换行符)
        body = line[:tail_start]

        if self._quote != "":
            # 处于多行字符串内部, 原样保留(只更新状态)
            self._scan(body)
            return line

        if body.strip().startswith("#"):
            # shebang 和编码声明需要保留
            if body.lstrip().startswith("#!") or self.ENCODING_RE.search(body):
                return line
            return None

        code, cut = self._scan(body)
        if code.strip() == "":
            return None
        if cut:
            return code.rstrip() + tail
        return line

    def _scan(self, text: str) -> Tuple[str, bool]:
        """扫描一行内容, 返回 (去掉行尾注释后的内容, 是否命中注释)

        同时维护 self._quote / self._escaped 支持跨行的三引号字符串
        """
        i = 0
        size = len(text)
        while i < size:
            ch = text[i]
            if self._escaped:
                self._escaped = False
                i += 1
                continue
            if self._quote != "":
                quote = self._quote
                if text.startswith(quote, i):
                    self._quote = ""
                    i += len(quote)
                    continue
                if ch == "\\":
                    self._escaped = True
                i += 1
                continue
            if ch in ("'", '"'):
                if text.startswith(ch * 3, i):
                    self._quote = ch * 3
                    i += 3
                    continue
                self._quote = ch
                i += 1
                continue
            if ch == "\\":
                self._escaped = True
                i += 1
                continue
            if ch == "#":
                return text[:i], True
            i += 1
        return text, False


class XnotePack:
    """Xnote代码打包工具,可以把多个文件打包成一个文件

    过滤选项:
    - skip_blank_line: 忽略空行(默认开启)
    - skip_comment: 忽略注释(整行注释 + 行尾注释), 保留 shebang 和编码声明(默认关闭)
    """

    def __init__(self, root_dir="", skip_blank_line=True, skip_comment=False):
        self.encoding = "utf-8"
        self.import_dict = {}
        self.entry_file = ""
        self.packed_files = set()
        self.root_dir = root_dir
        self.skip_blank_line = skip_blank_line
        self.skip_comment = skip_comment
        self.from_import_re = re.compile(r"from\s+\.(\w+)\s+import\s+(.+)")

    def _get_abs_path(self, fpath: str):
        if fpath.startswith("."):
            fpath = os.path.join(self.root_dir, fpath)
        return os.path.abspath(fpath)

    def set_entry_file(self, entry_file=""):
        self.entry_file = self._get_abs_path(entry_file)

    def add_import_file(self, line, fpath):
        self.import_dict[line] = self._get_abs_path(fpath)

    def add_import_star(self, module_name=""):
        line = f"from .{module_name} import *"
        fpath = f"./{module_name}.py"
        self.add_import_file(line, fpath)

    def build(self, target_file=""):
        lines = self._do_build([], self.entry_file)
        parent_dir = os.path.dirname(target_file)
        if parent_dir != "":
            os.makedirs(parent_dir, exist_ok=True)
        with open(target_file, "w+", encoding=self.encoding) as fp:
            fp.writelines(lines)

    def _do_build(self, lines: Optional[List[str]] = None, entry_file: str = "") -> List[str]:
        if lines is None:
            lines = []
        comment_filter = CommentFilter(self.skip_comment)
        with open(entry_file, "r+", encoding=self.encoding) as fp:
            for line in fp.readlines():
                line_strip = line.strip()
                result = self.from_import_re.match(line)
                if result:
                    from_file = result.groups()[0]
                    import_modules = result.groups()[1]
                    if import_modules.strip() != "*":
                        print(f"WARN: ignore import part: {import_modules}")
                        line_strip = f"from .{from_file} import *"
                    self.add_import_star(from_file)
                replace_file = self.import_dict.get(line_strip)
                if replace_file in self.packed_files:
                    print(f"file already packed: {replace_file}")
                    continue
                new_line = comment_filter.handle(line)
                if new_line is None:
                    # 整行都是注释
                    continue
                line = new_line
                line_strip = line.strip()
                if line_strip == "" and self.skip_blank_line:
                    continue
                if replace_file != None:
                    self.packed_files.add(replace_file)
                    replace_file_relative = fsutil.get_relative_path(replace_file, self.root_dir)
                    lines.append(f"# include start {replace_file_relative}\n")
                    self._do_build(lines, replace_file)
                    lines.append(f"# include end {replace_file_relative}\n")
                else:
                    lines.append(line)
        return lines


PluginPack = XnotePack


def test_pack():
    pack = XnotePack("./your_plugin_dir/", skip_comment=True)
    pack.set_entry_file("./page_main.py")
    pack.build("dist/your_plugin.py")
