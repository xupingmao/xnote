# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-09-03 00:09:00
@LastEditors  : xupingmao
@LastEditTime : 2024-09-03 00:09:00
@FilePath     : /xnote/xnote/webui/tree.py
@Description  : 树形组件
"""

from typing import List

from xnote.webui.base import BaseComponent, BaseContainer
from xnote.webui.container import TextContainer
from xutils import escape_html


class TreeNode(BaseComponent):
    """树节点，可以包含子节点"""

    def __init__(self, text="", href="", icon_class="", value="",
                 css_class="", expanded=False, badge_info="", onclick=""):
        self.text = text
        self.href = href
        self.icon_class = icon_class
        self.value = value
        self.css_class = css_class
        self.expanded = expanded
        self.badge_info = badge_info
        self.onclick = onclick
        self.children: List[TreeNode] = []
        self.extra = TextContainer(css_class="float-right")

    def add(self, node: "TreeNode") -> "TreeNode":
        self.children.append(node)
        return self

    def add_node(self, text="", href="", icon_class="", value="",
                 expanded=False, css_class="", badge_info="", onclick="") -> "TreeNode":
        """创建并添加一个子节点，返回新创建的子节点"""
        node = TreeNode(text=text, href=href, icon_class=icon_class, value=value,
                        expanded=expanded, css_class=css_class, badge_info=badge_info,
                        onclick=onclick)
        self.children.append(node)
        return node

    def render(self) -> str:
        has_children = len(self.children) > 0

        li_class = "x-tree-node"
        if self.expanded:
            li_class += " x-tree-open"
        if self.css_class:
            li_class += " " + self.css_class

        out = []
        out.append(f'<li class="{li_class}">')

        # 折叠/展开开关
        if has_children:
            out.append('<span class="x-tree-toggle" onclick="xnote.tree.toggle(this)"></span>')
        else:
            out.append('<span class="x-tree-toggle x-tree-toggle-empty"></span>')

        # 图标
        if self.icon_class:
            out.append(f'<i class="{escape_html(self.icon_class)}"></i>')

        # 文本 / 链接
        text = escape_html(self.text)
        if self.href:
            onclick_attr = f' onclick="{escape_html(self.onclick)}"' if self.onclick else ""
            out.append(f'<a class="x-tree-link" href="{escape_html(self.href)}"{onclick_attr}>{text}</a>')
        elif self.onclick:
            out.append(f'<a class="x-tree-link" href="javascript:;" onclick="{escape_html(self.onclick)}">{text}</a>')
        else:
            out.append(f'<span class="x-tree-label">{text}</span>')

        # 角标
        if self.badge_info:
            out.append(f'<span class="badge-info">{escape_html(self.badge_info)}</span>')

        # 右侧操作区
        extra_html = self.extra.render()
        if extra_html:
            out.append(extra_html)

        # 子节点
        if has_children:
            out.append('<ul class="x-tree-children">')
            for child in self.children:
                out.append(child.render())
            out.append('</ul>')

        out.append('</li>')
        return "".join(out)


class Tree(BaseContainer):
    """树形容器，包含多个顶层节点"""

    _script = """
<script>
(function(){
    if (!window.xnote) { window.xnote = {}; }
    if (xnote.tree) { return; }
    xnote.tree = {
        toggle: function(el) {
            var li = el.parentNode;
            if (li && li.className.indexOf("x-tree-open") >= 0) {
                li.className = li.className.replace(" x-tree-open", "");
            } else if (li) {
                li.className = li.className + " x-tree-open";
            }
        }
    };
})();
</script>
"""

    def __init__(self, css_class="", id=""):
        super().__init__(css_class=f"x-tree {css_class}", id=id)

    def add_node(self, text="", href="", icon_class="", value="",
                 expanded=False, css_class="", badge_info="", onclick="") -> TreeNode:
        """添加一个顶层节点，返回该节点"""
        node = TreeNode(text=text, href=href, icon_class=icon_class, value=value,
                        expanded=expanded, css_class=css_class, badge_info=badge_info,
                        onclick=onclick)
        self.children.append(node)
        return node

    @classmethod
    def build_from_list(cls, data: List[dict], text_key="name", children_key="children",
                        href_key="", value_key="", icon_key="") -> "Tree":
        """从嵌套的字典列表构建树

        :param data: 形如 [{"name": "节点", "children": [...]}]
        :param text_key: 文本字段名
        :param children_key: 子节点字段名
        :param href_key: 链接字段名，为空则忽略
        :param value_key: 值字段名，为空则忽略
        :param icon_key: 图标字段名，为空则忽略
        """
        tree = cls()

        def _build(items: List[dict]) -> List[TreeNode]:
            nodes = []
            for item in items:
                node = TreeNode(
                    text=item.get(text_key, ""),
                    href=item.get(href_key, "") if href_key else "",
                    value=item.get(value_key, "") if value_key else "",
                    icon_class=item.get(icon_key, "") if icon_key else "",
                )
                children = item.get(children_key, [])
                if children:
                    for child in _build(children):
                        node.add(child)
                nodes.append(node)
            return nodes

        for node in _build(data):
            tree.children.append(node)
        return tree

    def render(self) -> str:
        if self.is_empty():
            return ""

        attr_list = ""
        if self.css_style:
            attr_list = f'style="{self.css_style}"'
        if self.id:
            attr_list += f" id={self.id}"

        out = []
        out.append(f'<ul class="{self.css_class}" {attr_list}>')
        for item in self.children:
            out.append(item.render())
        out.append('</ul>')

        # 折叠/展开的 JS（内部 IIFE 已做幂等保护，可重复输出）
        out.append(Tree._script)

        return "".join(out)
