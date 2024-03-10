# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-03-10 16:20:05
@LastEditors  : xupingmao
@LastEditTime : 2024-03-10 21:29:41
@FilePath     : /xnote/xnote/core/template/table.py
@Description  : 描述
"""


class TableHead:
    def __init__(self):
        self.title = ""
        self.field = ""
        self.link_field = ""
        self.type = ""
        self.width = "auto"

class TableAction:
    def __init__(self):
        self.title = ""
        self.type = ""
        self.link_field = ""
        self.title_field = ""
        self.css_class=""
        self.msg_field = ""
        self.default_msg = ""
    
    def get_title(self, row):
        assert isinstance(row, dict)
        if self.title_field == "":
            return self.title
        return row.get(self.title_field)
    
    def get_msg(self, row):
        assert isinstance(row, dict)
        if self.msg_field == "":
            return self.default_msg
        return row.get(self.msg_field)
    
class DataTable:
    """数据表格"""
    
    def __init__(self):
        self.heads = []
        self.rows = []
        self.actions = []
    
    def add_head(self, title="", field = "", type="", link_field="", width="auto"):
        head = TableHead()
        head.title = title
        head.field = field
        head.type = type
        head.width = width
        head.link_field = link_field
        self.heads.append(head)
        
    def add_row(self, obj):
        assert isinstance(obj, dict)
        self.rows.append(obj)
        
    def set_rows(self, rows):
        assert isinstance(rows, list)
        for row in rows:
            assert isinstance(row, dict)
        self.rows = rows
    
    def add_action(self, title="", type="button", link_field="", title_field="", msg_field="", css_class=""):
        action = TableAction()
        action.title = title
        action.type = type
        action.link_field = link_field
        action.title_field = title_field
        action.css_class = css_class
        action.msg_field = msg_field
        
        self.actions.append(action)


