# -*- coding:utf-8 -*-
"""后端 HTML 片段接口测试。

原来由前端 art-template 渲染的模板已迁移为后端(Tornado)渲染并通过接口返回 HTML 片段,
本文件覆盖这些新增的片段接口。

注意: 测试框架的 request() 用 len(urlencode(data)) 作为 CONTENT_LENGTH, 非 ASCII 的
POST body 会被截断, 因此 HTTP 层用例使用 ASCII 文本; 中文/格式化相关的断言通过直接
调用 handler 方法来覆盖。
"""
import unittest

try:
    import test_base
    from test_base import login_test_user, logout_test_user, request_html
except ImportError:
    from tests import test_base
    from tests.test_base import login_test_user, logout_test_user, request_html

app = test_base.init()


class BaseFragmentTestCase(unittest.TestCase):

    def setUp(self):
        login_test_user("admin")

    def tearDown(self):
        # 不要登出账号，其他测试要用
        pass

    def http_html(self, url, method="GET", data=None):
        ret = request_html(url, method, data)
        assert isinstance(ret, bytes)
        return ret.decode("utf-8")


class TestMarkdownOutlineFragment(BaseFragmentTestCase):
    """编辑侧栏大纲片段: POST /note/api/markdown/outline"""

    def get_handler(self):
        # init() 之后 xtables 已初始化, 可以正常 import
        from xnote_handlers.note.note_api import MarkdownOutlineHandler
        return MarkdownOutlineHandler()

    def test_parse_headings_basic(self):
        handler = self.get_handler()
        text = "# 一级标题\n普通文本\n## 二级标题"
        headings = handler.parse_headings(text)

        self.assertEqual(2, len(headings))
        self.assertEqual(1, headings[0].level)
        self.assertEqual(1, headings[0].lineNo)
        self.assertEqual("一级标题", headings[0].name)
        self.assertEqual(2, headings[1].level)
        self.assertEqual(3, headings[1].lineNo)
        self.assertEqual("二级标题", headings[1].name)

    def test_parse_headings_skip_code_block(self):
        handler = self.get_handler()
        text = "# A\n```python\n# not heading\n```\n### B"
        headings = handler.parse_headings(text)

        self.assertEqual(["A", "B"], [h.name for h in headings])
        self.assertEqual([1, 5], [h.lineNo for h in headings])
        self.assertEqual([1, 3], [h.level for h in headings])

    def test_format_name_trim(self):
        handler = self.get_handler()
        self.assertEqual("标题", handler.format_name("##   标题  "))
        self.assertEqual("标题", handler.format_name("## **标题**"))

        level, name = handler.parse_heading("### Admin")
        self.assertEqual(3, level)
        self.assertEqual("Admin", name)

    def test_http_outline(self):
        # HTTP 层使用 ASCII 文本, 避免 POST body 被截断
        text = "# Title\nbody\n## Sub\n```\n# fake\n```\n### Deep"
        html = self.http_html("/note/api/markdown/outline", "POST", dict(text=text))

        self.assertIn('class="list-item level-1"', html)
        self.assertIn('data-line="1"', html)
        self.assertIn("<span>Title</span>", html)
        self.assertIn('class="list-item level-2"', html)
        self.assertIn('data-line="3"', html)
        self.assertIn("<span>Sub</span>", html)
        self.assertIn('class="list-item level-3"', html)
        self.assertIn('data-line="7"', html)
        self.assertIn("<span>Deep</span>", html)
        # 代码块内的 # 不当作标题
        self.assertNotIn("fake", html)

    def test_http_outline_empty(self):
        html = self.http_html("/note/api/markdown/outline", "POST", dict(text=""))
        self.assertEqual("", html.strip())


class TestNoteGroupFragment(BaseFragmentTestCase):
    """笔记本树/移动分组片段: /api/v1/note/group/{tree_html,select_html}"""

    def test_group_select_html(self):
        html = self.http_html("/api/v1/note/group/select_html?orderby=name")
        self.assertIn("note-group-select", html)

    def test_group_tree_html_contains_group(self):
        from tests.test_base_note import create_note_for_test, delete_note_for_test

        name = "test_group_tree_html"
        delete_note_for_test(name)
        group_id = create_note_for_test("group", name)

        try:
            html = self.http_html("/api/v1/note/group/tree_html")
            self.assertIn("book-item", html)
            self.assertIn(name, html)
            self.assertIn('data-id="%s"' % group_id, html)
        finally:
            delete_note_for_test(name)


class TestNoteTagFragment(BaseFragmentTestCase):
    """标签管理片段: /note/tag/{suggest_html,delete_html}

    不使用 test_base_note.get_default_group_id(), 因为它依赖可能存在脏数据的
    "default_group_id" 笔记; 这里自己创建唯一的分组并在结束时清理, 保证用例可重复执行。
    """

    def create_group(self, name):
        from tests.test_base_note import create_note_for_test, delete_note_for_test
        delete_note_for_test(name)
        return create_note_for_test("group", name)

    def remove_group(self, name):
        from tests.test_base_note import delete_note_for_test
        delete_note_for_test(name)

    def test_tag_suggest_html(self):
        name = "test_tag_suggest_group"
        group_id = self.create_group(name)
        try:
            html = self.http_html("/note/tag/suggest_html?group_id=%s" % group_id)

            self.assertIn("标签", html)
            self.assertIn("全部", html)
            self.assertIn("/note/manage?parent_id=%s" % group_id, html)
        finally:
            self.remove_group(name)

    def test_tag_delete_html(self):
        name = "test_tag_delete_group"
        group_id = self.create_group(name)
        try:
            html = self.http_html("/note/tag/delete_html?group_id=%s" % group_id)

            # 没有标签时只输出容器
            self.assertIn("card btn-line-height", html)
        finally:
            self.remove_group(name)


class TestFsOptionDialogFragment(BaseFragmentTestCase):
    """文件操作对话框片段: GET /fs/dialog/option"""

    def test_option_dialog(self):
        html = self.http_html("/fs/dialog/option?path=/tmp/test.txt")

        self.assertIn("下载", html)
        self.assertIn("重命名", html)
        self.assertIn("删除", html)
        self.assertIn('data-path="/tmp/test.txt"', html)
        self.assertIn("xnote.dialog.closeByElement(this)", html)


class TestFsTextContentsFragment(BaseFragmentTestCase):
    """book 目录片段: GET /fs_text?method=contents_html"""

    def test_contents_html_without_path(self):
        html = self.http_html("/fs_text?method=contents_html")
        self.assertEqual("path不能为空", html)


if __name__ == "__main__":
    unittest.main()
