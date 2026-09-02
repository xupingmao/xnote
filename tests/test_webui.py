# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/07/18 18:36:23
# @modified 2021/07/18 19:45:09
# @filename test_search.py

from . import test_base
from .test_base import json_request_return_dict
from xnote.core import xauth
from xnote.core import xtables
from xnote_handlers.plugin.dao import add_visit_log, delete_visit_log
from xnote.webui import Div
from xnote.webui import Tree, TreeNode

import xutils

app = test_base.init()
json_request = test_base.json_request
request_html = test_base.request_html
BaseTestCase = test_base.BaseTestCase

class TestMain(BaseTestCase):

    def test_div_recursive(self):
        a = Div()
        b = Div()
        
        a.add(b)
        b.add(a)
        
        try:
            a.render()
            assert False
        except Exception as e:
            xutils.print_exc()
            assert "too deep depth" in str(e)


class TestTree(BaseTestCase):

    def test_empty_tree(self):
        tree = Tree()
        assert tree.render() == ""

    def test_simple_node(self):
        tree = Tree()
        tree.add_node(text="根节点", href="/api/note/1")
        html = tree.render()
        assert "x-tree" in html
        assert "根节点" in html
        assert 'href="/api/note/1"' in html
        assert "x-tree-children" not in html

    def test_nested_node(self):
        tree = Tree()
        root = tree.add_node(text="根节点")
        child = root.add_node(text="子节点")
        child.add_node(text="孙节点")
        html = tree.render()
        assert html.count("x-tree-node") == 3
        assert html.count("x-tree-children") == 2
        # 没有节点处于展开状态（避免误判脚本里也包含 "x-tree-open" 字符串）
        assert '<li class="x-tree-node x-tree-open"' not in html

    def test_expanded_node(self):
        tree = Tree()
        root = tree.add_node(text="根节点", expanded=True)
        root.add_node(text="子节点")
        html = tree.render()
        assert "x-tree-open" in html

    def test_build_from_list(self):
        data = [
            {"name": "A", "href": "/a", "children": [
                {"name": "A1", "href": "/a1"}
            ]},
            {"name": "B", "icon": "fa fa-folder"},
        ]
        tree = Tree.build_from_list(data, href_key="href", icon_key="icon")
        html = tree.render()
        assert "A" in html and "A1" in html and "B" in html
        assert 'href="/a"' in html
        assert "fa fa-folder" in html

    def test_badge_info(self):
        tree = Tree()
        tree.add_node(text="节点", badge_info="99")
        html = tree.render()
        assert "badge-info" in html
        assert "99" in html


class TestTreeExamplePage(BaseTestCase):

    def test_example_tree_page(self):
        html = request_html("/test/example/tree")
        html = html.decode("utf-8")
        assert "x-tree" in html
        assert "我的笔记" in html
        assert "Tree树形组件" in html
        