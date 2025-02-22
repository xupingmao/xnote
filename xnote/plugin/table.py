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
import typing
import re

DEFAULT_WIDTH = "auto"

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


class DefaultHeadStyle:
    def __init__(self):
        self.width = DEFAULT_WIDTH
        self.min_width = ""
        self.max_width = ""

    def get_width(self, width=""):
        if width == DEFAULT_WIDTH or width == "":
            return self.width
        return width

DEFAULT_HEAD_STYLE = DefaultHeadStyle()

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
        self.max_width = ""
        self.min_width = ""
        self.css_class_field = ""
        self.detail_field = ""
        self.table = table
        self.default_style = DEFAULT_HEAD_STYLE
    
    def get_css_class(self, row: dict):
        return row.get(self.css_class_field, "")
    
    def get_link(self, row: dict):
        return row.get(self.link_field)
    
    def has_link(self, row: dict):
        if self.link_field == "":
            return False
        link = self.get_link(row)
        return link not in (None, "")
    
    def has_detail(self, row: dict):
        if self.detail_field == "":
            return False
        detail = self.get_detail(row)
        value = row.get(self.field)
        if detail == value:
            return False
        return detail not in (None, "")
    
    def get_detail(self, row: dict):
        return row.get(self.detail_field)

    def _get_min_width(self) -> typing.Optional[str]:
        if self.min_width != "":
            return self.min_width
        
        default_style = self.default_style
        if default_style.min_width != "":
            return default_style.min_width
        
        match = self.min_width_pattern.match(self.width)
        if match:
            return match.groups()[0]
        return None
    
    def _get_max_width(self):
        if self.max_width != "":
            return self.max_width
        return self.default_style.max_width
    
    def _fix_width_weight(self):
        """如果有一个head设置了权重,没有设置的head权重默认为1"""
        if self.width_weight == 0:
            self.width_weight = 1
        return self.width_weight
    
    def get_style(self):
        result = []
        min_width = self._get_min_width()
        if min_width != None:
            result.append(f"min-width: {min_width}")
        
        if self.width_weight > 0:
            percent = self.width_weight / self.table._get_width_weight_total()
            result.append(f"width: {percent*100:.2f}%")
        else:
            result.append(f"width: {self.width}")

        max_width = self._get_max_width()
        if max_width != "":
            result.append(f"max-width: {max_width}")
        
        return ";".join(result)
    
    def get_min_width_int(self):
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
        self.css_class = "" # action操作自身(比如链接/按钮之类的)的css类
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
        self.title = "表格明细"
        self.create_btn_text = "新增记录"
        self.heads = [] # type:list[TableHead]
        self.rows = []
        self.actions = []
        self.action_head = TableHead(self)
        self.default_head_style = DefaultHeadStyle()
        self.action_head.default_style = self.default_head_style
    
    def add_head(self, title="", field = "", type="", link_field="", 
                 width=DEFAULT_WIDTH, width_weight=0, min_width="", max_width="",
                 css_class_field="", link_target="", detail_field=""):
        """添加表头

        Arguments:
            - title: 标题
            - field: 字段名
            - type: (optional) 类型
            - link_field: (optional) 链接的字段名
            - width: (optional) 宽度设置
            - width_weight: (optional) 宽度权重,如果设置会覆盖width设置
            - min_width: (optional) 最小的宽度
            - max_width: (optional) 最大的宽度
            - css_class_field: (optional) css类的字段名
            - link_target: 链接的target属性(css属性) @see `LinkTargetType`
        """
        default_style = self.default_head_style

        head = TableHead(self)
        head.title = title
        head.field = field
        head.type = type
        head.width = default_style.get_width(width)
        head.min_width = min_width
        head.max_width = max_width
        head.width_weight = width_weight
        head.link_field = link_field
        head.link_target = link_target
        head.css_class_field = css_class_field
        head.detail_field = detail_field
        head.default_style = self.default_head_style
        self.heads.append(head)
        
    def add_row(self, obj):
        assert isinstance(obj, dict)
        self.rows.append(obj)
        
    def set_rows(self, rows):
        assert isinstance(rows, list)
        for row in rows:
            assert isinstance(row, dict)
        self.rows = rows

    def set_action_style(self, width="auto", width_weight=0, min_width="", max_width=""):
        action_head = self.action_head
        action_head.width = width
        action_head.width_weight = width_weight
        action_head.min_width = min_width
        action_head.max_width = max_width
    
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
            min_width += head.get_min_width_int()
        return max(min_width, 300)

    def _get_width_weight_total(self):
        total = 0
        for head in self.heads:
            total += head._fix_width_weight()
        total += self.action_head._fix_width_weight()
        return total

