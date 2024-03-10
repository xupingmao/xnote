# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-03-10 16:20:05
@LastEditors  : xupingmao
@LastEditTime : 2024-03-10 17:30:44
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
    
    def add_action(self, title="", action_url="", new_link=False):
        pass

