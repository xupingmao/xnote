# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-03-10 16:20:05
@LastEditors  : xupingmao
@LastEditTime : 2024-04-21 19:15:41
@FilePath     : /xnote/xnote/plugin/table.py
@Description  : 描述
"""

class TableActionType:
    """表格动作的类型"""
    link = "link"
    button = "button"
    confirm = "confirm"
    edit_form = "edit_form"

class TableHead:
    """表格的标题单元"""
    def __init__(self):
        self.title = ""
        self.field = ""
        self.link_field = ""
        self.type = ""
        self.width = "auto"
        self.css_class_field = ""
    
    def get_css_class(self, row):
        return row.get(self.css_class_field, "")
    
    def get_link(self, row):
        return row.get(self.link_field)
    
    def has_link(self, row):
        if self.link_field == "":
            return False
        link = self.get_link(row)
        return link not in (None, "")
    
class TableAction:
    """表格的操作单元"""
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
    
    def get_link(self, row):
        return row.get(self.link_field)
    
    def has_link(self, row):
        if self.link_field == "":
            return False
        link = self.get_link(row)
        return link not in (None, "")

class DataTable:
    """数据表格"""
    
    def __init__(self):
        self.heads = []
        self.rows = []
        self.actions = []
    
    def add_head(self, title="", field = "", type="", link_field="", width="auto", css_class_field=""):
        head = TableHead()
        head.title = title
        head.field = field
        head.type = type
        head.width = width
        head.link_field = link_field
        head.css_class_field = css_class_field
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
        return action



