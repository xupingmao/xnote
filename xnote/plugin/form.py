# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-03-10 16:20:05
@LastEditors  : xupingmao
@LastEditTime : 2024-03-31 14:17:08
@FilePath     : /xnote/xnote/plugin/form.py
@Description  : 描述
"""

class FormRowType:
    """表单行的类型"""
    input = "input"
    select = "select"
    textarea = "textarea"
    date = "date"

class FormRowOption:
    """表单行的选项"""
    def __init__(self):
        self.title = ""
        self.value = ""

class FormRowDateType:
    """日期的类型"""
    year = "year"
    month = "month"
    date = "date"
    time = "time"
    datetime = "datetime"
    default = date

class FormRow:
    """数据行"""
    def __init__(self):
        self.id = ""
        self.title = ""
        self.field = ""
        self.placeholder = ""
        self.value = ""
        self.type = FormRowType.input
        self.css_class = ""
        self.options = []
        self.date_type = FormRowDateType.date # 用于日期组件
        self.readonly = False
    
    def add_option(self, title="", value=""):
        option = FormRowOption()
        option.title = title
        option.value = value
        self.options.append(option)
        return self

    def get_readonly_attr(self):
        if self.readonly:
            return "readonly"
        else:
            return ""
    
class DataForm:
    """数据表格"""
    
    def __init__(self):
        self.id = "0"
        self.row_id = 0
        self.rows = []
        self.save_action = "save"
        self.model_name = "default"
    
    def add_row(self, title="", field="", placeholder="", value="", type="input", css_class="", readonly=False):
        self.row_id += 1
        row = FormRow()
        row.id = f"row_{self.id}_{self.row_id}"
        row.title = title
        row.field = field
        row.placeholder = placeholder
        row.value = value
        row.type = type
        row.css_class = css_class
        row.readonly = readonly
        
        self.rows.append(row)
        return row

    def count_type(self, type=""):
        count = 0
        for item in self.rows:
            if item.type == type:
                count+=1
        return count

