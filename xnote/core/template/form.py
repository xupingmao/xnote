# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-03-10 16:20:05
@LastEditors  : xupingmao
@LastEditTime : 2024-03-16 16:45:12
@FilePath     : /xnote/xnote/core/template/form.py
@Description  : 描述
"""

class FormRow:
    """数据行"""
    def __init__(self):
        self.title = ""
        self.field = ""
        self.placeholder = ""
        self.value = ""
        self.type = "input"
    
class DataForm:
    """数据表格"""
    
    def __init__(self):
        self.id = "0"
        self.rows = []
    
    def add_row(self, title="", field="", placeholder="", value="", type="input"):
        row = FormRow()
        row.title = title
        row.field = field
        row.placeholder = placeholder
        row.value = value
        row.type = type
        
        self.rows.append(row)
