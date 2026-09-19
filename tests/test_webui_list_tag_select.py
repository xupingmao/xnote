# -*- coding: utf-8 -*-
"""TagSelect / ListViewTagSelect 渲染测试（tag 风格选择器，支持独立使用）"""
from . import test_base
from xnote.webui import ListView, TagSelect
from xnote.webui._list import ListViewTagSelect

app = test_base.init()
BaseTestCase = test_base.BaseTestCase


def _to_str(html):
    if isinstance(html, bytes):
        return html.decode("utf-8")
    return html


class TestTagSelect(BaseTestCase):
    """通用 TagSelect 组件（可独立使用）"""

    def test_standalone_single(self):
        ts = TagSelect(text="状态", name="status", value="1", multiple=False)
        ts.add_option("进行中", "1").add_option("已完成", "2").add_option("已取消", "3")
        html = _to_str(ts.render())
        assert "tag-select" in html
        assert "list-item" not in html          # 独立使用不带 list-item
        assert 'data-value="1"' in html
        assert 'class="tag lightblue active"' in html
        assert html.count('class="tag lightblue active"') == 1
        assert 'name="status"' in html

    def test_standalone_multiple(self):
        ts = TagSelect(text="标签", name="tags", value=["1", "2"], multiple=True)
        ts.add_option("A", "1").add_option("B", "2").add_option("C", "3")
        html = _to_str(ts.render())
        assert 'data-multiple="true"' in html
        assert html.count('class="tag lightblue active"') == 2  # 1,2 选中

    def test_standalone_readonly(self):
        ts = TagSelect(text="只读", name="r", value="1", readonly=True)
        ts.add_option("X", "1")
        html = _to_str(ts.render())
        assert 'data-readonly="1"' in html


class TestListViewTagSelect(BaseTestCase):
    """ListView 内的 tag 选择器行（复用 TagSelect）"""

    def test_render_as_list_item(self):
        lv = ListView()
        ts = lv.add_tag_select(text="状态", name="status", value="1", multiple=False)
        ts.add_option("进行中", "1").add_option("已完成", "2").add_option("已取消", "3")
        ts2 = lv.add_tag_select(text="标签", name="tags", value=["1", "2"], multiple=True)
        ts2.add_option("A", "1").add_option("B", "2")

        html = _to_str(lv.render())
        assert "list-tag-select" in html
        assert "list-item" in html               # 列表行带 list-item
        assert "tag-select" in html              # 同时带通用 class
        assert 'data-value="1"' in html
        # 单选 value=1 + 多选 [1,2] => 共 3 个 active
        assert html.count('class="tag lightblue active"') == 3
        assert "进行中" in html and "已完成" in html
        assert 'name="status"' in html

    def test_readonly_row(self):
        ts3 = ListViewTagSelect(text="只读", name="r", value="1", readonly=True)
        ts3.add_option("X", "1")
        h3 = _to_str(ts3.render())
        assert "list-item" in h3
        assert 'data-readonly="1"' in h3
