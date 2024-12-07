# encoding=utf-8
import os
import re
from xutils import fsutil

class XnotePack:
    """Xnote代码打包工具,可以把多个文件打包成一个文件"""
    def __init__(self, root_dir=""):
        self.encoding="utf-8"
        self.import_dict = {}
        self.entry_file = ""
        self.packed_files = set()
        self.root_dir = root_dir
        self.skip_blank_line = True
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
        with open(target_file, "w+", encoding=self.encoding) as fp:
            fp.writelines(lines)
    
    def _do_build(self, lines=[], entry_file=""):
        # type: (list[str], str) -> list[str]
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
    pack = XnotePack("./your_plugin_dir/")
    pack.set_entry_file("./page_main.py")
    pack.build("dist/your_plugin.py")