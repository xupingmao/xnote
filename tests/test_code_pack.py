# -*- coding: utf-8 -*-
"""Coverage tests for xutils/code/pack.py

打包工具只依赖文件系统, 不依赖服务, 用临时目录完成打包后再断言结果。
"""
import os
import shutil
import tempfile
import unittest

from xutils.code.pack import CommentFilter, XnotePack

ENTRY_CODE = '''#!/usr/bin/env python3
# encoding=utf-8
"""入口模块, 文档里的 # 号不是注释"""

# 顶部整行注释
from .util import *

def main():  # 行尾注释
    name = "hello # not comment"  # 真正的注释
    tip = f"a{b}#c"
    text = """
    多行字符串里的 # 号
    # 看起来像注释的一行
    """
    return name, tip, text  # return
'''

UTIL_CODE = '''# util 模块
# 另一行注释

KEY = "value#hash"   # 常量

def add(a, b):
    """加法"""
    return a + b  # 返回和
'''


class TestCodePack(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.plugin_dir = os.path.join(self.tmp_dir, "plugin")
        os.makedirs(self.plugin_dir)
        self._write("page_main.py", ENTRY_CODE)
        self._write("util.py", UTIL_CODE)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _write(self, name, content):
        fpath = os.path.join(self.plugin_dir, name)
        with open(fpath, "w", encoding="utf-8") as fp:
            fp.write(content)
        return fpath

    def _pack(self, skip_comment=False):
        pack = XnotePack(self.plugin_dir, skip_comment=skip_comment)
        pack.set_entry_file("./page_main.py")
        target = os.path.join(self.tmp_dir, "dist", "plugin.py")
        pack.build(target)
        with open(target, encoding="utf-8") as fp:
            return fp.read()

    def test_default_keep_comment(self):
        content = self._pack()
        self.assertIn("# 顶部整行注释", content)
        self.assertIn("def main():  # 行尾注释", content)
        self.assertIn('KEY = "value#hash"   # 常量', content)

    def test_skip_comment(self):
        content = self._pack(skip_comment=True)
        self.assertNotIn("# 顶部整行注释", content)
        self.assertNotIn("# 函数内注释", content)
        self.assertNotIn("# 真正的注释", content)
        self.assertNotIn("# 返回和", content)
        self.assertNotIn("# util 模块", content)

    def test_skip_comment_keep_code(self):
        content = self._pack(skip_comment=True)
        self.assertIn("def main():", content)
        self.assertIn('name = "hello # not comment"', content)
        self.assertIn('tip = f"a{b}#c"', content)
        self.assertIn('KEY = "value#hash"', content)
        self.assertIn("return a + b", content)

    def test_skip_comment_keep_special_comment(self):
        content = self._pack(skip_comment=True)
        self.assertIn("#!/usr/bin/env python3", content)
        self.assertIn("# encoding=utf-8", content)
        self.assertIn('"""入口模块, 文档里的 # 号不是注释"""', content)
        self.assertIn("# 看起来像注释的一行", content)
        self.assertIn("# include start util.py", content)
        self.assertIn("# include end util.py", content)

    def test_skip_blank_line(self):
        content = self._pack()
        self.assertNotIn("\n\n", content)


class TestCommentFilter(unittest.TestCase):

    def test_disabled(self):
        comment_filter = CommentFilter(skip_comment=False)
        self.assertEqual(comment_filter.handle("a = 1  # comment\n"), "a = 1  # comment\n")

    def test_comment_line(self):
        comment_filter = CommentFilter(skip_comment=True)
        self.assertIsNone(comment_filter.handle("# comment\n"))
        self.assertIsNone(comment_filter.handle("    # comment\n"))

    def test_inline_comment(self):
        comment_filter = CommentFilter(skip_comment=True)
        self.assertEqual(comment_filter.handle("a = 1  # comment\n"), "a = 1\n")

    def test_string_with_sharp(self):
        comment_filter = CommentFilter(skip_comment=True)
        self.assertEqual(comment_filter.handle('a = "#123"\n'), 'a = "#123"\n')

    def test_multiline_string(self):
        comment_filter = CommentFilter(skip_comment=True)
        self.assertEqual(comment_filter.handle('a = """\n'), 'a = """\n')
        self.assertEqual(comment_filter.handle('# not comment\n'), '# not comment\n')
        self.assertEqual(comment_filter.handle('"""\n'), '"""\n')
        self.assertEqual(comment_filter.handle("b = 1  # comment\n"), "b = 1\n")


if __name__ == "__main__":
    unittest.main()
