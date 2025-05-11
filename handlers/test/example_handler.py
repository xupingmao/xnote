# encoding=utf-8
# Created by xupingmao on 2024/09/15
import xutils
from xutils import Storage
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xmanager
from xnote.core import xconfig
from xnote.plugin.table_plugin import BaseTablePlugin
from xnote.plugin import DataTable, TableActionType, TabBox


def get_example_tab():
    server_home = xconfig.WebConfig.server_home
    tab = TabBox(tab_key="name", title="案例:", css_class="btn-style")
    tab.add_tab("文本示例", value="text", href=f"{server_home}/test/example?name=text")
    tab.add_tab("按钮示例", value="btn", href=f"{server_home}/test/example?name=btn")
    tab.add_tab("Tab示例", value="tab", href=f"{server_home}/test/example?name=tab")
    tab.add_tab("Tag示例", value="tag", href=f"{server_home}/test/example?name=tag")
    tab.add_tab("Dialog示例", value="dialog", href=f"{server_home}/test/example?name=dialog")
    tab.add_tab("Dropdown示例", value="dropdown", href=f"{server_home}/test/example?name=dropdown")
    tab.add_tab("Table示例", value="table", href=f"{server_home}/test/example/table?name=table")
    tab.add_tab("Hammer示例", value="hammer", href=f"{server_home}/test/example?name=hammer")
    return tab

class TableExampleHandler(BaseTablePlugin):
    
    title = "表格测试"

    show_aside = False

    PAGE_HTML = """
{% include test/component/example_nav_tab.html %}

<div class="card">
    {% raw tab.render() %}
</div>

<div class="card">
    <form>
        <div class="row">
            <div class="input-group">
                <label>类型</label>
                <select name="prefix" value="">
                    <option value="">全部</option>
                    <option value="">类型-1</option>
                    <option value="">类型-2</option>
                </select>
            </div>

            <div class="input-group">
                <label>关键字</label>
                <input type="text"/>
            </div>
        </div>

        <div class="row">
            <input type="button" class="btn do-search-btn" value="查询数据">
            <a class="btn btn-default" href="">重置查询</a>
        </div>

    </form>
</div>

<div class="card">
    {% include common/table/table_v2.html %}
</div>

<div class="card">
    {% set-global xnote_table_var = "weight_table" %}
    {% include common/table/table_v2.html %}
</div>

<div class="card">
    {% set-global xnote_table_var = "empty_table" %}
    {% include common/table/table_v2.html %}
</div>
"""

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

        kw.weight_table = self.get_weight_table()
        kw.empty_table = self.get_empty_table()
        kw.tab = self.get_tab_component()
        kw.example_tab = get_example_tab()

        return self.response_page(**kw)
    
    def get_tab_component(self):
        tab = TabBox(tab_key="tab", tab_default="2", css_class="btn-style", title="后端tab组件")
        tab.add_tab(title="选项1", value="1", href="?tab=1")
        tab.add_tab(title="选项2", value="2")
        tab.add_tab(title="选项3", value="3", css_class="hide")
        tab.add_tab(title="onclick", href="#", onclick="javascript:alert('onclick!')")
        return tab
    
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
        table.title = "表格3-空表格"
        table.create_btn_text = "新建"
        table.add_head("权重1", field="value1", width_weight=1)
        table.add_head("权重1", field="value2", width_weight=1)
        table.add_head("权重2", field="value3", width_weight=2)
        table.add_head("权重1", field="value4", width_weight=1)
        table.add_action("编辑", link_field="edit_url", type=TableActionType.edit_form)
        table.add_action("删除", link_field="delete_url", type=TableActionType.confirm, 
                         msg_field="delete_msg", css_class="btn danger")
        return table

class ExampleHandler:

    def GET(self):
        user_name = xauth.current_name_str()
        xmanager.add_visit_log(user_name, "/test/example")
        
        name = xutils.get_argument_str("name", "")
        example_tab = get_example_tab()

        if name == "":
            return xtemplate.render("test/page/example_index.html", example_tab=example_tab)
        else:
            return xtemplate.render(f"test/page/example_{name}.html", example_tab=example_tab)

    def POST(self):
        return self.GET()


xurls = (
    r"/test/example", ExampleHandler,
    r"/test/example/table", TableExampleHandler,
)