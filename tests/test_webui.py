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
from xnote.webui import Dropdown, DropdownOption
from xnote.webui import TextTag, DialogForm
from xnote.webui.table import DataTable, TableRowType
from xnote.plugin import DataForm

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
        tree.add_node(text="根节点", href="/api/v1/note/1")
        html = tree.render()
        assert "x-tree" in html
        assert "根节点" in html
        assert 'href="/api/v1/note/1"' in html
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


class TestTextTag(BaseTestCase):

    def test_render_normal(self):
        html = TextTag(text="标签", css_class="lightgray").render()
        assert '<span class="tag lightgray">标签</span>' == html

    def test_render_active(self):
        html = TextTag(text="标签", css_class="lightblue", active=True).render()
        assert '<span class="tag lightblue active">标签</span>' == html

    def test_render_active_no_css_class(self):
        html = TextTag(text="标签", active=True).render()
        assert '<span class="tag active">标签</span>' == html

    def test_render_with_href(self):
        html = TextTag(text="标签", css_class="lightred", href="/x", active=True).render()
        assert '<span class="tag lightred active"><a href="/x">标签</a></span>' == html


class TestDialogForm(BaseTestCase):

    def test_is_dataform_alias(self):
        # DialogForm 是 DataForm 的语义化别名，专用于弹窗场景
        form = DialogForm()
        assert isinstance(form, DataForm)
        assert form.form_type == "edit"

    def test_render_form_only(self):
        # 渲染表单片段（含自身的 保存/关闭 页脚按钮），但不包含弹窗触发按钮
        form = DialogForm()
        form.add_row("名称", "name", value="x")
        html = form.render().decode("utf-8")
        assert 'class="x-form"' in html
        assert 'name="name"' in html
        # 表单自身的页脚按钮
        assert "xnote.submitFormSave(this)" in html
        # 不应含有弹窗触发逻辑（那是 EditFormButton 的职责）
        assert "xnote.table.handleEditForm" not in html
        assert "打开弹窗表单" not in html


class TestDataTable(BaseTestCase):

    def test_image_type_render_thumbnail(self):
        table = DataTable()
        table.add_head(title="封面", field="cover", type=TableRowType.image)
        table.set_rows([{"cover": "/files/test.jpg"}])

        html = table.render().decode("utf-8")
        # 缩略图class
        assert "table-thumbnail" in html
        # 缩略图src
        assert 'src="/files/test.jpg"' in html
        # 点击查看原图
        assert 'data-origin="/files/test.jpg"' in html
        assert "xnote.table.handleViewImage(this)" in html

    def test_image_type_empty_value(self):
        table = DataTable()
        table.add_head(title="封面", field="cover", type=TableRowType.image)
        table.set_rows([{"cover": ""}])

        html = table.render().decode("utf-8")
        assert "table-thumbnail" not in html

    def test_image_type_enum(self):
        from xnote.webui.table import TableRowEnum
        info = TableRowEnum.get_by_name(TableRowType.image)
        assert info != None
        assert info.min_width == "80px"

    def test_add_image_head(self):
        table = DataTable()
        table.add_image_head("图标", "icon")
        assert len(table.heads) == 1
        head = table.heads[0]
        assert head.title == "图标"
        assert head.field == "icon"
        assert head.type == TableRowType.image

        table.set_rows([{"icon": "/files/test.jpg"}])
        html = table.render().decode("utf-8")
        assert "table-thumbnail" in html
        assert 'src="/files/test.jpg"' in html

    def test_link_cell_render(self):
        table = DataTable()
        table.add_head(title="名称", field="name", link_field="url")
        table.set_rows([{"name": "百度", "url": "/open?q=1&t=2"}])

        html = table.render().decode("utf-8")
        # 链接被渲染且特殊字符被转义
        assert 'href="/open?q=1&amp;t=2"' in html
        assert ">百度</a>" in html

    def test_detail_cell_render(self):
        table = DataTable()
        table.add_head(title="内容", field="content", detail_field="detail")
        table.set_rows([{"content": "摘要", "detail": "完整内容"}])

        html = table.render().decode("utf-8")
        assert "查看详情" in html
        assert 'data-detail="完整内容"' in html

    def test_action_button_render(self):
        from xnote.webui.table import TableActionType
        table = DataTable()
        table.add_head(title="名称", field="name")
        table.add_action(title="编辑", type=TableActionType.button, link_field="edit_url")
        table.set_rows([{"name": "x", "edit_url": "/api/v1/edit/1"}])

        html = table.render().decode("utf-8")
        assert "操作" in html
        assert 'onclick="xnote.table.handleAction(this)"' in html
        assert 'data-url="/api/v1/edit/1"' in html
        assert ">编辑</button>" in html

    def test_cell_escaping(self):
        table = DataTable()
        table.add_head(title="名称", field="name")
        table.set_rows([{"name": '<script>alert(1)</script>'}])

        html = table.render().decode("utf-8")
        assert "&lt;script&gt;" in html
        assert "<script>alert(1)</script>" not in html


class TestDropdown(BaseTestCase):

    def test_dropdown_option_render(self):
        option = DropdownOption(name="选项A", value="a")
        html = option.render()
        assert '<option value="a">选项A</option>' == html

    def test_dropdown_render(self):
        dropdown = Dropdown()
        dropdown.add_option(name="选项A", value="a")
        dropdown.add_option(name="选项B", value="b")
        html = dropdown.render().decode("utf-8")
        assert "<select>" in html
        assert '<option value="a">选项A</option>' in html
        assert '<option value="b">选项B</option>' in html

    def test_dropdown_empty_render(self):
        dropdown = Dropdown()
        html = dropdown.render().decode("utf-8")
        assert "<select></select>" == html.replace("\n", "").replace(" ", "")
        

class TestDataForm(BaseTestCase):

    def test_add_image_render(self):
        form = DataForm()
        form.add_image("封面图片", "cover")
        html = form.render().decode("utf-8")

        assert 'data-upload-kind="image"' in html
        assert 'name="cover"' in html
        assert 'accept="image/*"' in html
        assert "添加图片" in html
        assert "添加附件" not in html

    def test_add_file_render(self):
        form = DataForm()
        form.add_file("附件", "attachments")
        html = form.render().decode("utf-8")

        assert 'data-upload-kind="file"' in html
        assert 'name="attachments"' in html
        assert "添加附件" in html
        # 文件类型不限制 accept
        assert 'accept="image/*"' not in html

    def test_upload_value_roundtrip(self):
        # 编辑已有记录：传入已有 webpath 列表，应正确回显为预览项
        form = DataForm()
        webpaths = ["/data/files/admin/a.png", "/data/files/admin/b.jpg"]
        form.add_image("封面图片", "cover", value=webpaths)
        html = form.render().decode("utf-8")

        # 隐藏 input 保存逗号分隔的 webpath
        assert 'value="/data/files/admin/a.png,/data/files/admin/b.jpg"' in html
        # 预览缩略图
        assert 'data-src="/data/files/admin/a.png"' in html
        assert 'src="/data/files/admin/a.png?mode=thumbnail"' in html
        assert 'data-src="/data/files/admin/b.jpg"' in html

        # value_list 正确
        row = form.rows[-1]
        assert row.value_list[0]["webpath"] == "/data/files/admin/a.png"
        assert row.value_list[0]["name"] == "a.png"

    def test_upload_value_from_comma_string(self):
        form = DataForm()
        form.add_file("附件", "attachments", value="/data/x.pdf,/data/y.zip")
        row = form.rows[-1]
        assert len(row.value_list) == 2
        assert row.value == "/data/x.pdf,/data/y.zip"
        assert row.value_list[1]["name"] == "y.zip"

    def test_example_form_has_upload(self):
        # 示例表单页（/test/example/table?action=edit）应渲染出上传组件
        body = request_html("/test/example/table?action=edit").decode("utf-8")
        assert 'data-upload-kind="image"' in body
        assert 'data-upload-kind="file"' in body
        assert "添加图片" in body
        assert "添加附件" in body
