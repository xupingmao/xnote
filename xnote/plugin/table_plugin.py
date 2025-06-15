# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-03-31 11:17:36
@LastEditors  : xupingmao
@LastEditTime : 2024-09-16 16:08:37
@FilePath     : /xnote/xnote/plugin/table_plugin.py
@Description  : 描述
"""

import xutils
import json
from xnote.core.xtemplate import BasePlugin
from xutils import Storage
from xutils import webutil
from xnote.plugin import DataForm, FormRowType, FormRowDateType, DataTable, TableActionType


class ParamDict:

    """参数字典,在dict的基础上增加了类型方法"""
    def __init__(self, dict_value: dict):
        self.dict = dict_value

    def get_int(self, key: str, default_value=0):
        return int(self.dict.get(key, default_value))
    
    def get_float(self, key: str, default_value=0.0):
        return float(self.dict.get(key, default_value))
    
    def get_str(self, key: str, default_value="", strip = True):
        result = str(self.dict.get(key, default_value))
        if strip:
            return result.strip()
        return result

    def get(self, key: str):
        return self.dict.get(key)
    

class BaseTablePlugin(BasePlugin):
    rows = 0
    show_edit = False

    # 增加引用,方便子类调用
    FormRowType = FormRowType
    FormRowDateType = FormRowDateType
    TableActionType = TableActionType

    # 导航html
    NAV_HTML = """
<div class="card">
    <button class="btn" onclick="xnote.table.handleEditForm(this)"
        data-url="?action=edit" data-title="新增记录">新增记录</button>
</div>
"""
    # 表格html
    TABLE_HTML = """
<div class="card">
    {% include common/table/table.html %}
</div>

{% init page_max = 0 %}
{% if page_max > 0 %}
    <div class="card">
        {% include common/pagination.html %}
    </div>
{% end %}
"""

    # 编辑表单的html
    EDIT_HTML = """
<div class="card">
    {% include common/form/form.html %}
</div>
"""

    # 最终渲染的html, 如果不设置, 等价于 NAV_HTML + TABLE_HTML
    PAGE_HTML = ""
    
    def get_page_html(self):
        """可以通过重写这个方法实现自定义的页面"""
        if self.PAGE_HTML == "":
            return self.NAV_HTML + self.TABLE_HTML
        return self.PAGE_HTML

    @classmethod
    def rebuild_page_html(cls):
        cls.PAGE_HTML = cls.NAV_HTML + cls.TABLE_HTML

    def response_form(self, **kw):
        return self.response_ajax(self.EDIT_HTML, **kw)

    def response_page(self, **kw):
        page_html = self.get_page_html()
        self.writehtml(page_html, **kw)

    def handle(self, input=""):
        action = xutils.get_argument_str("action")
        method = getattr(self, "handle_" + action, None)
        if method != None:
            return method()
        return self.handle_page()

    def handle_edit(self):
        form = self.create_form()
        form.add_row("id", "id", css_class="hide")
        form.add_row("只读属性", "readonly_attr", value="test", readonly=True)

        row = form.add_row("类型", "type", type=FormRowType.select)
        row.add_option("类型1", "1")
        row.add_option("类型2", "2")
        
        form.add_row("标题", "title")
        form.add_row("日期", "date", type=FormRowType.date)
        form.add_row("内容", "content", type=FormRowType.textarea)
        
        kw = Storage()
        kw.form = form
        return self.response_form(**kw)
    
    def get_param_dict(self) -> ParamDict:
        data = xutils.get_argument_str("data")
        data_dict = json.loads(data)
        return ParamDict(data_dict)
    
    get_data_dict = get_param_dict
    
    def handle_save(self):
        # data_dict = self.get_data_dict()
        return webutil.FailedResult(code="500", message="Not Implemented")
    
    def handle_page(self):
        table = self.create_table()
        table.add_head("类型", "type", css_class_field="type_class")
        table.add_head("标题", "title", link_field="view_url")
        table.add_head("日期", "date")
        table.add_head("内容", "content")

        table.add_action("编辑", link_field="edit_url", type=TableActionType.edit_form)
        table.add_action("删除", link_field="delete_url", type=TableActionType.confirm, msg_field="delete_msg", css_class="btn danger")

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

        return self.response_page(**kw)

    def handle_delete(self):
        # data_id = xutils.get_argument_int("data_id")
        return webutil.FailedResult(code="500", message="Not Implemented")
    
    def create_table(self):
        return DataTable()

    def create_form(self):
        return DataForm()

