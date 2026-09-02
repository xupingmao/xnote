# encoding=utf-8
# Created by xupingmao on 2024/09/03
# @description 树形组件(Tree)的示例
import xutils

from xutils import Storage
from xnote.plugin.table_plugin import BasePlugin
from xnote.webui import Tree, TreeNode
from xnote.webui import TextLink, ConfirmActionLink
from xnote_handlers.config import LinkConfig

BODY_HTML = """
{% include test/component/example_nav_tab.html %}

<div class="card">
    <span class="card-title">Tree: 手动构建（嵌套节点 / 图标 / 角标 / 操作链接）</span>
    {% render tree_manual %}
</div>

<div class="card">
    <span class="card-title">Tree: 默认展开</span>
    {% render tree_expanded %}
</div>

<div class="card">
    <span class="card-title">Tree: 从嵌套字典列表构建 (build_from_list)</span>
    {% render tree_from_list %}
</div>
"""


class TreeExampleHandler(BasePlugin):
    title = "Tree树形组件"
    rows = 0
    parent_link = LinkConfig.develop_index

    def handle(self, input=""):
        # 1. 手动构建：支持嵌套、图标、角标、右侧操作链接
        tree_manual = Tree()
        root = tree_manual.add_node(text="我的笔记", icon_class="fa fa-folder", badge_info="12")
        doc = root.add_node(text="文档", icon_class="fa fa-folder", href="/note/group?name=doc")
        doc.add_node(text="读书笔记", href="/note/view?name=read")
        doc.add_node(text="工作记录", href="/note/view?name=work")
        root.add_node(text="回收站", icon_class="fa fa-trash", href="/note/trash")

        # 给根节点添加右侧操作链接
        root.extra.add(TextLink(text="新建", href="?action=create"))
        root.extra.add(ConfirmActionLink(text="删除", url="?action=delete", msg="确认删除笔记分组吗?"))

        # 2. 默认展开的树
        tree_expanded = Tree()
        node = tree_expanded.add_node(text="展开的根节点", expanded=True, icon_class="fa fa-folder-open")
        node.add_node(text="子节点A", icon_class="fa fa-file-text-o")
        node.add_node(text="子节点B", icon_class="fa fa-file-text-o")

        # 3. 从嵌套字典列表构建
        data = [
            {"name": "项目", "icon": "fa fa-folder", "children": [
                {"name": "xnote", "href": "/note/view?name=xnote", "children": [
                    {"name": "架构设计", "href": "/note/view?name=arch"},
                    {"name": "开发计划", "href": "/note/view?name=plan"},
                ]},
                {"name": "blog", "href": "/note/view?name=blog"},
            ]},
            {"name": "教程", "icon": "fa fa-book", "href": "/note/view?name=tutorial"},
        ]
        tree_from_list = Tree.build_from_list(data, icon_key="icon")

        kw = Storage()
        kw.example_tab = self.get_example_tab()
        kw.tree_manual = tree_manual
        kw.tree_expanded = tree_expanded
        kw.tree_from_list = tree_from_list

        self.writehtml(html=BODY_HTML, **kw)

    def get_example_tab(self):
        from .example_handler import get_example_tab
        return get_example_tab(tab_default="tree")


xurls = (
    r"/test/example/tree", TreeExampleHandler,
)
