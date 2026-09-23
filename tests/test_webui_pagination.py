# -*- coding:utf-8 -*-
"""分页相关组件的测试

覆盖:
1. add_url_param / remove_url_param 的拼接与替换语义
2. Pagination 的 page_arg_name 参数、默认使用当前页面URL
3. DataTable / ListView 通过 set_pagination 支持分页
"""
from . import test_base
from .test_base import request_html

from xutils.textutil import add_url_param, remove_url_param
from xnote.webui import Pagination, ListView, ListItem
from xnote.webui.table import DataTable

app = test_base.init()
BaseTestCase = test_base.BaseTestCase


def _to_str(html):
    if isinstance(html, bytes):
        return html.decode("utf-8")
    return str(html)


class TestUrlParam(BaseTestCase):

    def test_add_param_without_query(self):
        self.assertEqual("/note/view?page=2", add_url_param("/note/view", "page", 2))

    def test_add_param_with_query(self):
        self.assertEqual("/note/view?id=1&page=2",
                         add_url_param("/note/view?id=1", "page", 2))

    def test_add_param_replace(self):
        """同名参数应该被替换, 而不是追加出两个同名参数"""
        self.assertEqual("/note/view?page=3",
                         add_url_param("/note/view?page=1", "page", 3))
        # 被替换的参数追加到末尾, 其它参数的顺序保持不变
        self.assertEqual("/note/view?type=a&x=1&page=3",
                         add_url_param("/note/view?page=1&type=a&x=1", "page", 3))

    def test_add_param_empty_url(self):
        self.assertEqual("?page=1", add_url_param("", "page", 1))

    def test_add_param_keep_encoded_value(self):
        """已有的转义不能被二次编码破坏"""
        self.assertEqual("/a?dbpath=data%2Ftest.db&page=1",
                         add_url_param("/a?dbpath=data%2Ftest.db", "page", 1))

    def test_remove_param(self):
        self.assertEqual("/a?x=1", remove_url_param("/a?x=1&page=2", "page"))
        self.assertEqual("/a?x=1", remove_url_param("/a?page=2&x=1", "page"))
        self.assertEqual("", remove_url_param("?page=2", "page"))
        self.assertEqual("/a", remove_url_param("/a", "page"))


class TestPagination(BaseTestCase):

    def test_default_page_arg_name(self):
        html = _to_str(Pagination(page=2, page_max=5, page_url="/a?type=x").render())
        self.assertIn("/a?type=x&amp;page=1", html)
        self.assertIn("/a?type=x&amp;page=3", html)
        self.assertIn("/a?type=x&amp;page=5", html)

    def test_custom_page_arg_name(self):
        html = _to_str(Pagination(page=1, page_max=5, page_url="/a",
                                  page_arg_name="comment_page").render())
        self.assertIn("comment_page=2", html)
        self.assertNotIn("?page=", html)

    def test_build_page_url(self):
        pagination = Pagination(page=1, page_max=5, page_url="/a?type=x")
        self.assertEqual("/a?type=x&page=3", pagination.build_page_url(3))

        pagination2 = Pagination(page=1, page_max=5, page_url="/a",
                                 page_arg_name="comment_page")
        self.assertEqual("/a?comment_page=2", pagination2.build_page_url(2))

    def test_legacy_page_url_with_page_suffix(self):
        """兼容旧的 `?page=` / `?type=x&page=` 写法, 不会拼出 `?page=&page=2`"""
        pagination = Pagination(page=1, page_max=5, page_url="?page=")
        self.assertEqual("?page=2", pagination.build_page_url(2))

        pagination2 = Pagination(page=1, page_max=5, page_url="?type=x&page=")
        self.assertEqual("?type=x&page=2", pagination2.build_page_url(2))

    def test_page_url_default_to_current_url(self):
        """page_url 不设置时, 生成的链接应基于当前页面(离线环境为空)"""
        pagination = Pagination(page=1, page_max=5)
        # 非web环境下取不到当前URL, 退化为相对URL
        self.assertEqual("?page=2", pagination.build_page_url(2))

    def test_page_max_from_total(self):
        self.assertEqual(5, Pagination(page=1, page_total=100, page_size=20).get_page_max())
        self.assertEqual(1, Pagination(page=1, page_total=0).get_page_max())

    def test_page_from_page_current(self):
        """兼容只传 page_current 的写法"""
        pagination = Pagination(page_current=3, page_max=5, page_url="/a")
        self.assertEqual(3, pagination.page)
        self.assertEqual("/a?page=4", pagination.build_page_url(4))

    def test_page_str_param(self):
        """分页参数是字符串时不能报错"""
        pagination = Pagination(page="2", page_max="5", page_url="/a")
        self.assertEqual(2, pagination.page)
        self.assertEqual(5, pagination.get_page_max())


class TestDataTablePagination(BaseTestCase):

    def _create_table(self):
        table = DataTable()
        table.add_head("名称", "name")
        table.add_row({"name": "test"})
        return table

    def test_no_pagination_by_default(self):
        table = self._create_table()
        self.assertEqual("", table.render_pagination_html())
        html = _to_str(table.render())
        self.assertNotIn("pagenation", html)

    def test_render_pagination(self):
        table = self._create_table()
        pagination = table.set_pagination(page=1, page_total=100, page_size=20)
        self.assertIsNotNone(pagination)
        # 没有传 page_max 时由 page_total/page_size 推导
        self.assertEqual(5, pagination.get_page_max())

        html = _to_str(table.render())
        self.assertIn("pagenation", html)
        self.assertIn("100条记录", html)
        self.assertIn("?page=2", html)

    def test_pagination_page_url(self):
        table = self._create_table()
        table.set_pagination(page=2, page_total=100, page_url="/note/list?type=a")
        html = _to_str(table.render())
        self.assertIn("/note/list?type=a&amp;page=3", html)

    def test_pagination_page_arg_name(self):
        table = self._create_table()
        table.set_pagination(page=1, page_total=100, page_url="/note/list",
                             page_arg_name="comment_page")
        html = _to_str(table.render())
        self.assertIn("comment_page=2", html)


class TestListViewPagination(BaseTestCase):

    def _create_list_view(self):
        list_view = ListView()
        list_view.add_item(ListItem(text="item-1"))
        return list_view

    def test_no_pagination_by_default(self):
        list_view = self._create_list_view()
        self.assertEqual("", list_view.render_pagination_html())
        html = _to_str(list_view.render())
        self.assertNotIn("pagenation", html)

    def test_render_pagination(self):
        list_view = self._create_list_view()
        pagination = list_view.set_pagination(page=1, page_total=100, page_size=20)
        self.assertIsNotNone(pagination)
        self.assertEqual(5, pagination.get_page_max())

        html = _to_str(list_view.render())
        self.assertIn("pagenation", html)
        self.assertIn("?page=2", html)

    def test_pagination_page_arg_name(self):
        list_view = self._create_list_view()
        list_view.set_pagination(page=1, page_total=100, page_url="/note/list",
                                 page_arg_name="comment_page")
        html = _to_str(list_view.render())
        self.assertIn("comment_page=2", html)


class TestSetPaginationKwCompat(BaseTestCase):
    """兼容写法: 调用方直接把模板变量透传进来(set_pagination(**kw))

    比如 BaseListPlugin.response_page 会把 kw(list_view/page/page_max/filter_html...)
    整体透传给组件, 组件必须忽略自己不需要的参数, 不能直接抛 TypeError
    """

    def test_list_view_ignore_extra_kw(self):
        list_view = ListView()
        pagination = list_view.set_pagination(
            list_view=list_view, filter_html="<div/>", page=2, page_max=5,
            page_total=100, page_size=20, page_url="?type=a&page=")
        self.assertEqual(2, pagination.page)
        self.assertEqual(5, pagination.get_page_max())
        # 旧的 `?page=` 后缀写法不会拼出两个 page
        self.assertEqual("?type=a&page=3", pagination.build_page_url(3))

    def test_data_table_ignore_extra_kw(self):
        table = DataTable()
        pagination = table.set_pagination(
            table=table, page=3, page_max=5, page_url="/note/list")
        self.assertEqual(3, pagination.page)
        self.assertIn("pagenation", table.render_pagination_html())


class TestPaginationInPage(BaseTestCase):
    """页面级别: 分页链接默认基于当前页面的URL"""

    def test_table_example_page(self):
        body = request_html("/examples/table").decode("utf-8")
        self.assertIn("pagenation", body)
        # 默认的 page_url 是当前页面的URL
        self.assertIn("/examples/table?page=2", body)

    def test_list_plugin_example_page(self):
        body = request_html("/examples/list_plugin?tab=all").decode("utf-8")
        self.assertIn("pagenation", body)
        # 保留当前页面的其它参数
        self.assertIn("/examples/list_plugin?tab=all&amp;page=2", body)

    def test_list_plugin_example_page_with_page(self):
        """page_url 基于当前URL时要去掉已有的 page 参数, 不能出现两个 page"""
        body = request_html("/examples/list_plugin?tab=all&page=3").decode("utf-8")
        self.assertIn("/examples/list_plugin?tab=all&amp;page=2", body)
        self.assertNotIn("page=3&amp;page=2", body)

    def test_business_list_page_with_legacy_kw(self):
        """业务列表页仍在 kw 里透传 page/page_max/page_size, 不能被无关参数带崩

        例如 BaseListPlugin.response_page(list_view=..., filter_html=..., page=..., page_max=...)
        会把整个 kw 透传给 list_view.set_pagination
        """
        body = request_html("/todo").decode("utf-8")
        self.assertIn("pagenation", body)
