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
import re

class TableActionType:
    """表格动作的类型"""
    link = "link"
    button = "button"
    confirm = "confirm"
    edit_form = "edit_form"

class LinkTargetType:
    """a标签的target属性枚举"""
    blank = "_blank"
    self_ = "_self"
    parent = "_parent"
    top = "_top"


def _get_px_value(value: str):
    """获取像素px的数字值,内部函数,请勿使用"""
    if value.endswith("px"):
        return int(value.strip("px"))
    return 0

class TableHead:
    # 最小宽度
    min_width_pattern = re.compile(r"min:([0-9]+px)")
    # 权重
    width_weight_pattern = re.compile(r"weight:([0-9]+)")

    """表格的标题单元"""
    def __init__(self, table: "DataTable"):
        self.title = ""
        self.field = ""
        self.link_field = ""
        self.link_target = ""
        self.type = ""
        self.width = "auto"
        self.width_weight = 0
        self.css_class_field = ""
        self.table = table
    
    def get_css_class(self, row: dict):
        return row.get(self.css_class_field, "")
    
    def get_link(self, row: dict):
        return row.get(self.link_field)
    
    def has_link(self, row: dict):
        if self.link_field == "":
            return False
        link = self.get_link(row)
        return link not in (None, "")
    

    def _get_min_width(self):
        match = self.min_width_pattern.match(self.width)
        if match:
            return match.groups()[0]
        return None
    
    def _fix_width_weight(self):
        """如果有一个head设置了权重,没有设置的head权重默认为1"""
        if self.width_weight == 0:
            self.width_weight = 1
        return self.width_weight
    
    def get_style(self):
        min_width = self._get_min_width()
        if min_width != None:
            return f"min-width: {min_width}"
        if self.width_weight > 0:
            percent = self.width_weight / self.table._get_width_weight_total()
            return f"width: {percent*100:.2f}%"
        return f"width: {self.width}"
    
    def get_min_width(self):
        min_width = self._get_min_width()
        if min_width:
            return _get_px_value(min_width)
        return _get_px_value(self.width)
    
class TableAction:
    """表格的操作单元"""
    def __init__(self):
        self.title = ""
        self.type = ""
        self.link_field = ""
        self.link_target = ""
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
        self.heads = [] # type:list[TableHead]
        self.rows = []
        self.actions = []
        self.action_head = TableHead(self)
    
    def add_head(self, title="", field = "", type="", link_field="", 
                 width="auto", width_weight=0, 
                 css_class_field="", link_target=""):
        head = TableHead(self)
        head.title = title
        head.field = field
        head.type = type
        head.width = width
        head.width_weight = width_weight
        head.link_field = link_field
        head.link_target = link_target
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

    def set_action_style(self, width="auto", width_weight=0):
        self.action_head.width = width
        self.action_head.width_weight = width_weight
    
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

    def get_min_width(self):
        min_width = 0
        for head in self.heads:
            min_width += head.get_min_width()
        return max(min_width, 300)

    def _get_width_weight_total(self):
        total = 0
        for head in self.heads:
            total += head._fix_width_weight()
        total += self.action_head._fix_width_weight()
        return total

