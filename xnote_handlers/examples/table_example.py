# encoding=utf-8
# Table 示例 tab，对应 /examples/example/table
import xutils
import copy

from xutils import Storage
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xmanager
from xnote.core import xconfig
from xnote.plugin.table_plugin import BaseTablePlugin, BasePlugin
from xnote.plugin import DataTable, TableActionType, TabBox, QueryForm, TabTable, DataForm, PageEditForm, DialogForm, EditFormButton
from xnote.webui import FormRowType
from xnote.plugin.table import InfoTable, InfoItem, ActionBar, TableRowType
from xnote.webui import ListView, ListItem, ConfirmButton, TextTag
from xutils import textutil
from xutils import webutil
from xutils.number_util import IntCounter
from xnote_handlers.config import LinkConfig
from .example_nav import get_example_tab

# 注意：from .example_handler import get_example_tab 已迁移到 example_nav.py


class TableExampleHandler(BaseTablePlugin):

    parent_link = LinkConfig.develop_index

    title = "表格测试"

    show_aside = False

    heading_count = IntCounter()

    PAGE_HTML = """
{% include examples/component/example_nav_tab.html %}

<div class="card">
    {% render tab %}
    {% render tab2 %}
</div>

<div class="card">
    {% render info_table %}
</div>

<div class="card">
    {% render query_form %}
</div>

<div class="card">
    {% include common/table/table_v2.html %}
</div>

<div class="card">
    {% set-global xnote_table_var = "weight_table" %}
    {% include common/table/table_v2.html %}
</div>

<div class="card">
    {% render empty_table %}
</div>

<div class="card">
    {% render image_table %}
</div>
"""

    tab_title_width = "120px"

    def handle_page(self):
        table = DataTable()
        table.title = "表格1-自动宽度"
        table.add_head("类型", "type", css_class_field="type_class")
        table.add_head("标题", "title", link_field="view_url")
        table.add_head("日期", "date")
        table.add_head("内容", "content")

        table.add_action("编辑", link_field="edit_url", type=TableActionType.edit_form)
        table.add_action("删除", link_field="delete_url", type=TableActionType.confirm,
                         msg_field="delete_msg", css_class="btn danger")

        row = {}
        row["type"] = "类型1"
        row["title"] = "测试"
        row["type_class"] = "red"
        row["date"] = "2020-01-01"
        row["content"] = "测试内容"
        row["view_url"] = "/note/index"
        row["edit_url"] = "?action=edit"
        row["delete_url"] = "?action=delete"
        row["delete_msg"] = "确认删除记录吗?"
        table.add_row(row)

        kw = Storage()
        kw.table = table
        kw.page = 1
        kw.page_max = 1
        kw.page_url = "?page="

        kw.query_form = self.get_query_form()
        kw.weight_table = self.get_weight_table()
        kw.empty_table = self.get_empty_table()
        kw.tab = self.get_tab_component()
        kw.tab2 = self.get_tab2()
        kw.example_tab = get_example_tab(tab_default="table")
        kw.info_table = self.get_info_table()
        kw.image_table = self.get_image_table()

        return self.response_page(**kw)

    def handle_edit(self):
        self.heading_count.add(1)
        show_heading = xutils.get_argument_bool("show_heading", True)

        form = self.create_form()

        if show_heading:
            form.add_heading("基础信息")

        form.add_row("id", "id", css_class="hide")
        form.add_row("只读属性", "readonly_attr", value="test", readonly=True)

        row = form.add_row("类型", "type", type=self.FormRowType.select)
        row.add_option("类型1", "1")
        row.add_option("类型2", "2")

        form.add_row("标题", "title")
        form.add_row("日期", "date", type=self.FormRowType.date)
        form.add_row("内容", "content", type=self.FormRowType.textarea)

        if show_heading:
            form.add_heading("高级信息")

        row = form.add_select("标签", field="tags", multiple=True, value=[1,2])
        row.add_option("标签1", "1")
        row.add_option("标签2", "2")
        row.add_option("标签3", "3")

        row = form.add_tag_select("标签(tag风格-单选)", field="tags2", value="1")
        row.add_option("标签1", "1")
        row.add_option("标签2", "2")
        row.add_option("标签3", "3")

        row = form.add_tag_select("标签(tag风格-多选)", field="tags3", multiple=True, value=["1", "2"])
        row.add_option("标签1", "1")
        row.add_option("标签2", "2")
        row.add_option("标签3", "3")

        form.add_row("备注信息")

        form.add_image("封面图片", "cover")
        form.add_file("附件", "attachments", multiple=True)

        kw = Storage()
        kw.form = form
        return self.response_form(**kw)

    def handle_save(self):
        data_dict = self.get_param_dict()
        return webutil.FailedResult(code="500", message=f"data_dict={data_dict}")

    def get_tab_component(self):
        tab = TabBox(
            tab_key="tab", tab_default="2", css_class="btn-style",
            title="后端tab组件", title_width=self.tab_title_width)
        tab.add_tab(title="选项1", value="1", href="?tab=1")
        tab.add_tab(title="选项2", value="2")
        tab.add_tab(title="选项3", value="3", css_class="hide")
        tab.add_tab(title="onclick", href="#", onclick="javascript:alert('onclick!')")
        return tab

    def get_tab2(self):
        tab = TabBox(
            tab_key="tab2", css_class="btn-style",
            title="状态", title_width=self.tab_title_width)
        tab.add_tab(title="正常", value="1")
        tab.add_tab(title="停用", value="2")
        return tab

    def get_query_form(self):
        type_str = xutils.get_argument_str("type")
        keyword = xutils.get_argument_str("keyword")
        date_str = xutils.get_argument_str("date")

        form = QueryForm()
        row = form.add_select(title="类型", field="type", value=type_str)
        row.add_option("类型-1", "1")
        row.add_option("类型-2", "2")
        form.add_row(title="关键字", field="keyword", value=keyword)
        form.add_date_input(title="日期", field="date", value=date_str)

        return form


    def get_weight_table(self):
        table = DataTable()
        table.title = "表格2-权重宽度"
        table.add_head("权重1", field="value1", width_weight=1)
        table.add_head("权重1", field="value2", width_weight=1)
        table.add_head("权重2", field="value3", width_weight=2)
        table.add_head("权重1", field="value4", width_weight=1)
        table.add_action("编辑", link_field="edit_url", type=TableActionType.edit_form)
        table.add_action("删除", link_field="delete_url", type=TableActionType.confirm,
                         msg_field="delete_msg", css_class="btn danger")

        row = {}
        row["value1"] = "value1"
        row["value2"] = "value2"
        row["value3"] = "value3"
        row["value4"] = "value4"
        row["view_url"] = "/note/index"
        row["edit_url"] = "?action=edit"
        row["delete_url"] = "?action=delete"
        row["delete_msg"] = "确认删除记录吗?"

        table.add_row(row)
        return table

    def get_empty_table(self):
        table = DataTable()
        table.add_head("权重1", field="value1", width_weight=1)
        table.add_head("权重1", field="value2", width_weight=1)
        table.add_head("权重2", field="value3", width_weight=2)
        table.add_head("权重1", field="value4", width_weight=1)
        table.add_action("编辑", link_field="edit_url", type=TableActionType.edit_form)
        table.add_action("删除", link_field="delete_url", type=TableActionType.confirm,
                         msg_field="delete_msg", css_class="btn danger")

        action_bar = table.action_bar
        action_bar.add_span(text="表格3-action_bar")
        action_bar.add_edit_button(text="新建", url="?action=edit", float_right=True)
        return table

    def get_info_table(self):
        table = InfoTable()
        table.cols = xutils.get_argument_int("cols", 2)
        table.add_item(InfoItem(name="组件名称", value="信息表格"))
        table.add_item(InfoItem(name="用途", value="展示对象的详细信息"))
        table.add_item(InfoItem(name="链接", value="xnote首页", href="/"))
        table.add_item(InfoItem(name="其他"))
        table.bottom_action_bar.add_edit_button("编辑1", "?action=edit&show_heading=true", css_class="btn-default")
        table.bottom_action_bar.add_edit_button("编辑2", "?action=edit&show_heading=false", css_class="btn-default")
        table.bottom_action_bar.add_confirm_button("删除", url="?action=delete", message="确认删除吗?", css_class="danger")
        return table

    def get_image_table(self):
        server_home = xconfig.WebConfig.server_home

        def image_url(path):
            return server_home + "/_static/" + path

        table = DataTable()
        table.title = "表格-图片类型"
        table.add_head("名称", "name")
        table.add_image_head("图标", "icon")
        table.add_head("说明", "desc")

        rows = [
            ("文件", "image/file.png", "普通文件图标"),
            ("文件夹", "image/folder2.png", "文件夹图标"),
            ("搜索", "image/icon_search.png", "搜索图标"),
            ("词典", "image/icon_dict.png", "词典图标"),
            ("游戏", "image/icons/icon_game.png", "游戏图标"),
            ("XNote", "xnote.png", "XNote 图标"),
            ("Favicon", "favicon.ico", "网站图标"),
        ]
        for name, path, desc in rows:
            table.add_row({"name": name, "icon": image_url(path), "desc": desc})
        return table


xurls = (
    r"/examples/example/table", TableExampleHandler,
)
