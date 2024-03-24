# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-03-10 16:20:05
@LastEditors  : xupingmao
@LastEditTime : 2024-03-24 11:01:58
@FilePath     : /xnote/xnote/core/template/form.py
@Description  : 描述
"""

class FormRowType:
    """表单行的类型"""
    input = "input"
    select = "select"
    textarea = "textarea"

class FormRowOption:
    """表单行的选项"""
    def __init__(self):
        self.title = ""
        self.value = ""

class FormRow:
    """数据行"""
    def __init__(self):
        self.title = ""
        self.field = ""
        self.placeholder = ""
        self.value = ""
        self.type = "input"
        self.css_class = ""
        self.options = []
    
    def add_option(self, title="", value=""):
        option = FormRowOption()
        option.title = title
        option.value = value
        self.options.append(option)
        return self
    
class DataForm:
    """数据表格"""
    
    def __init__(self):
        self.id = "0"
        self.rows = []
        self.save_action = "save"
    
    def add_row(self, title="", field="", placeholder="", value="", type="input", css_class=""):
        row = FormRow()
        row.title = title
        row.field = field
        row.placeholder = placeholder
        row.value = value
        row.type = type
        row.css_class = css_class
        
        self.rows.append(row)
        return row

