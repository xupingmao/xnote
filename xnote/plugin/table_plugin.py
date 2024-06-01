# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-03-31 11:17:36
@LastEditors  : xupingmao
@LastEditTime : 2024-06-01 12:48:38
@FilePath     : /xnote/xnote/plugin/table_plugin.py
@Description  : 描述
"""

import xutils
from xnote.core.xtemplate import BasePlugin
from xutils import Storage
from xutils import webutil
from xnote.plugin import DataForm, FormRowType, DataTable, TableActionType

class BaseTablePlugin(BasePlugin):
    rows = 0
    show_edit = False

    NAV_HTML = r"""
<div class="card">
    <button class="btn" onclick="xnote.table.handleEditForm(this)"
            data-url="?action=edit" data-title="新增记录">新增记录</button>
</div>
"""

    TABLE_HTML = r"""
<div class="card">
    {% include common/table/table.html %}
</div>

<div class="card">
    {% include common/pagination.html %}
</div>
"""

    EDIT_HTML = """
    <div class="card">
        {% include common/form/form.html %}
    </div>
    """

    PAGE_HTML = NAV_HTML + TABLE_HTML

    @classmethod
    def rebuild_page_html(cls):
        cls.PAGE_HTML = cls.NAV_HTML + cls.TABLE_HTML

    def response_form(self, **kw):
        return self.response_ajax(self.EDIT_HTML, **kw)

    def response_page(self, **kw):
        self.writehtml(self.PAGE_HTML, **kw)

    def handle(self, input=""):
        action = xutils.get_argument_str("action")
        method = getattr(self, "handle_" + action, None)
        if method != None:
            return method()
        return self.handle_page()

    def handle_edit(self):
        form = DataForm()
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
    
    def handle_save(self):
        return webutil.FailedResult(code="500", message="Not Implemented")
    
    def handle_page(self):
        table = DataTable()
        table.add_head("类型", "type")
        table.add_head("标题", "title", css_class_field="title_class")
        table.add_head("日期", "date")
        table.add_head("内容", "content")

        table.add_action("编辑", link_field="edit_url", type=TableActionType.edit_form)
        table.add_action("删除", link_field="delete_url", type=TableActionType.confirm, msg_field="delete_msg", css_class="btn danger")

        row = {}
        row["type"] = "类型1"
        row["title"] = "测试"
        row["title_class"] = "red"
        row["date"] = "2020-01-01"
        row["content"] = "测试内容"
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
        return webutil.FailedResult(code="500", message="Not Implemented")
