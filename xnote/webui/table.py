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
from typing import Any, List, Optional, Union

from xutils import textutil
from xnote.webui.base import BaseComponent, BaseContainer
from xnote.webui.container import ActionBar

from xnote.core import xtemplate
from web.utils import group  # type: ignore

def _escape(value: Any) -> str:
    """HTML转义,用于Python侧拼装的HTML片段(模板中通过{% raw %}输出,需要自行转义)"""
    if value is None:
        return ""
    return textutil.html_escape(str(value), quote=True)

DEFAULT_WIDTH = "auto"
DEFAULT_MIN_WIDTH = "100px"

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

class TableRowType:
    empty = ""
    date = "date"
    datetime = "datetime"
    image = "image"

class _TypeInfo:
    name: str
    min_width: str

    def __init__(self, name: str = "", min_width: str = ""):
        self.name = name
        self.min_width = min_width

class TableRowEnum:
    date = _TypeInfo(name="date", min_width="120px")
    datetime = _TypeInfo(name="datetime", min_width="200px")
    image = _TypeInfo(name="image", min_width="80px")

    _types = [date, datetime, image]

    @classmethod
    def get_by_name(cls, name: str = "") -> Optional[_TypeInfo]:
        for type_ in cls._types:
            if type_.name == name:
                return type_
        return None

def _get_px_value(value: str) -> int:
    """获取像素px的数字值,内部函数,请勿使用"""
    if value.endswith("px"):
        return int(value.strip("px"))
    return 0

class DefaultHeadStyle:
    width: str
    min_width: str
    max_width: str

    def __init__(self):
        self.width = DEFAULT_WIDTH
        self.min_width = DEFAULT_MIN_WIDTH
        self.max_width = ""

    def get_width(self, width: str = "") -> str:
        if width == DEFAULT_WIDTH or width == "":
            return self.width
        return width

DEFAULT_HEAD_STYLE = DefaultHeadStyle()

class TableHead:
    # 最小宽度
    min_width_pattern = re.compile(r"min:([0-9]+px)")
    # 权重
    width_weight_pattern = re.compile(r"weight:([0-9]+)")

    table: "DataTable"
    title: str
    field: str
    link_field: str
    link_target: str
    type: str
    width: str
    width_weight: int
    max_width: str
    min_width: str
    css_class_field: str
    detail_field: str
    default_style: DefaultHeadStyle

    """表格的标题单元"""
    def __init__(self, table: "DataTable"):
        self.table = table
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
        self.default_style = DEFAULT_HEAD_STYLE

    def get_css_class(self, row: dict) -> str:
        return row.get(self.css_class_field, "")

    def get_link(self, row: dict) -> Any:
        return row.get(self.link_field)

    def has_link(self, row: dict) -> bool:
        if self.link_field == "":
            return False
        link = self.get_link(row)
        return link not in (None, "")

    def has_detail(self, row: dict) -> bool:
        if self.detail_field == "":
            return False
        detail = self.get_detail(row)
        value = row.get(self.field)
        if detail == value:
            return False
        return detail not in (None, "")

    def get_detail(self, row: dict) -> Any:
        return row.get(self.detail_field)

    def get_cell_content(self, row: dict) -> str:
        """获取单元格的内部HTML(不含<td>标签)"""
        if self.type == TableRowType.image:
            value = row.get(self.field)
            if value not in (None, ""):
                escaped = _escape(value)
                return ('<img class="table-thumbnail" src="%s" data-origin="%s" '
                        'onclick="xnote.table.handleViewImage(this)" title="点击查看原图"/>'
                        % (escaped, escaped))
            return ""

        if self.has_link(row):
            link = self.get_link(row)
            return '<a href="%s" target="%s">%s</a>' % (
                _escape(link), _escape(self.link_target), _escape(row.get(self.field)))

        content = _escape(row.get(self.field))
        if self.has_detail(row):
            detail = self.get_detail(row)
            content += '<a data-detail="%s" onclick="xnote.table.handleViewDetail(this);">查看详情</a>' % _escape(detail)
        return content

    def render_cell(self, row: dict) -> str:
        """渲染单元格(含<td>标签)"""
        return '<td class="%s">%s</td>' % (_escape(self.get_css_class(row)), self.get_cell_content(row))

    def _get_min_width(self) -> Optional[str]:
        if self.min_width != "":
            return self.min_width

        type_info = TableRowEnum.get_by_name(self.type)
        if type_info:
            return type_info.min_width

        default_style = self.default_style
        if default_style.min_width != "":
            return default_style.min_width

        match = self.min_width_pattern.match(self.width)
        if match:
            return match.groups()[0]
        return None

    def _get_max_width(self) -> str:
        if self.max_width != "":
            return self.max_width
        return self.default_style.max_width

    def _fix_width_weight(self) -> int:
        """如果有一个head设置了权重,没有设置的head权重默认为1"""
        if self.width_weight == 0:
            self.width_weight = 1
        return self.width_weight

    def get_style(self) -> str:
        result = []  # type: List[str]
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

    def get_min_width_int(self) -> int:
        min_width = self._get_min_width()
        if min_width:
            return _get_px_value(min_width)
        return _get_px_value(self.width)

class TableAction:
    """表格的操作单元"""
    title: str
    type: str
    link_field: str
    link_target: str
    title_field: str
    css_class: str  # action操作自身(比如链接/按钮之类的)的css类
    msg_field: str
    default_msg: str

    def __init__(self):
        self.title = ""
        self.type = ""
        self.link_field = ""
        self.link_target = ""
        self.title_field = ""
        self.css_class = ""
        self.msg_field = ""
        self.default_msg = ""

    def get_title(self, row: dict) -> Any:
        if self.title_field == "":
            return self.title
        return row.get(self.title_field)

    def get_msg(self, row: dict) -> Any:
        if self.msg_field == "":
            return self.default_msg
        return row.get(self.msg_field)

    def get_link(self, row: dict) -> Any:
        return row.get(self.link_field)

    def has_link(self, row: dict) -> bool:
        if self.link_field == "":
            return False
        link = self.get_link(row)
        return link not in (None, "")

    def render_cell(self, row: dict) -> str:
        """渲染操作单元格的内容(不含<td>标签)"""
        link = self.get_link(row)
        if link == None:
            return ""
        title = self.get_title(row)
        if self.type == TableActionType.link:
            return '<a class="%s" href="%s" target="%s">%s</a>' % (
                _escape(self.css_class), _escape(link), _escape(self.link_target), _escape(title))
        if self.type == TableActionType.button:
            return ('<button class="btn-default %s" onclick="xnote.table.handleAction(this)" '
                    'data-url="%s" data-title="%s">%s</button>'
                    % (_escape(self.css_class), _escape(link), _escape(title), _escape(title)))
        if self.type == TableActionType.confirm:
            return ('<button class="btn-default %s" onclick="xnote.table.handleConfirmAction(this)" '
                    'data-url="%s" data-msg="%s">%s</button>'
                    % (_escape(self.css_class), _escape(link), _escape(self.get_msg(row)), _escape(title)))
        if self.type == TableActionType.edit_form:
            return ('<button class="btn-default %s" onclick="xnote.table.handleEditForm(this)" '
                    'data-url="%s" data-title="%s">%s</button>'
                    % (_escape(self.css_class), _escape(link), _escape(title), _escape(title)))
        return ""

class DataTable(BaseComponent):
    """数据表格"""

    title: str
    create_btn_text: str
    heads: List[TableHead]
    rows: List[dict]
    actions: List[TableAction]
    action_head: TableHead
    default_head_style: DefaultHeadStyle
    action_bar: ActionBar
    action_bar_html: Union[str, bytes]
    pagination_html: str

    def __init__(self):
        self.title = "表格名称"
        self.create_btn_text = "新增记录"
        self.heads = []  # type: List[TableHead]
        self.rows = []
        self.actions = []  # 操作列表
        self.action_head = TableHead(self)  # 操作表头
        self.default_head_style = DefaultHeadStyle()
        self.action_head.default_style = self.default_head_style

        # 操作栏
        self.action_bar = ActionBar()
        self.action_bar_html = ""  # type: Union[str, bytes]

        # 分页html
        self.pagination_html = ""

    def add_head(self, title: str = "", field: str = "", type: str = TableRowType.empty, link_field: str = "",
                 width: str = DEFAULT_WIDTH, width_weight: int = 0, min_width: str = "", max_width: str = "",
                 css_class_field: str = "", link_target: str = "", detail_field: str = "") -> None:
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

    def add_image_head(self, title: str = "", field: str = "", width: str = DEFAULT_WIDTH,
                      width_weight: int = 0, min_width: str = "", max_width: str = "") -> None:
        """添加图片类型的表头(等价于 add_head(..., type=TableRowType.image))"""
        self.add_head(title=title, field=field, type=TableRowType.image,
                      width=width, width_weight=width_weight, min_width=min_width, max_width=max_width)

    def add_row(self, obj: dict) -> None:
        self.rows.append(obj)

    def set_rows(self, rows: List[dict]) -> None:
        self.rows = rows

    def set_action_style(self, width: str = "auto", width_weight: int = 0, min_width: str = "", max_width: str = "") -> None:
        action_head = self.action_head
        action_head.width = width
        action_head.width_weight = width_weight
        action_head.min_width = min_width
        action_head.max_width = max_width

    def add_action(self, title: str = "", type: str = TableActionType.button, link_field: str = "", title_field: str = "", msg_field: str = "", css_class: str = "") -> TableAction:
        action = TableAction()
        action.title = title
        action.type = type
        action.link_field = link_field
        action.title_field = title_field
        action.css_class = css_class
        action.msg_field = msg_field
        self.actions.append(action)
        return action

    def get_min_width(self) -> int:
        min_width = 0
        for head in self.heads:
            min_width += head.get_min_width_int()
        return max(min_width, 300)

    def _get_width_weight_total(self) -> int:
        total = 0
        for head in self.heads:
            total += head._fix_width_weight()
        total += self.action_head._fix_width_weight()
        return total

    def render_heads_html(self) -> str:
        """渲染表头(<th>列表)"""
        parts = []  # type: List[str]
        for head in self.heads:
            parts.append('<th style="%s">%s</th>' % (_escape(head.get_style()), _escape(head.title)))
        if len(self.actions) > 0:
            parts.append('<th style="%s">操作</th>' % _escape(self.action_head.get_style()))
        return "\n".join(parts)

    def render_rows_html(self) -> str:
        """渲染数据行(<tr>列表)"""
        parts = []  # type: List[str]
        for row in self.rows:
            cells = []  # type: List[str]
            for head in self.heads:
                cells.append(head.render_cell(row))
            if len(self.actions) > 0:
                action_html = "".join(action.render_cell(row) for action in self.actions)
                cells.append("<td>%s</td>" % action_html)
            parts.append('<tr class="hover-tr">%s</tr>' % "".join(cells))
        return "\n".join(parts)

    def render(self) -> bytes:
        return xtemplate.render("common/table/table.html", table = self)

class InfoItem:
    name: str
    value: str
    href: str
    index: int

    def __init__(self, name: str = "", value: str = "", href: str = "", index: int = 0):
        self.name = name
        self.value = value
        self.href = href
        self.index = index

class InfoTable(BaseComponent):
    """信息表格,用于展示一个对象的信息"""

    cols: int
    items: List[InfoItem]
    bottom_action_bar: ActionBar

    def __init__(self):
        self.cols = 2  # 默认2列,这种最简单,各个设备都能正常展示
        self.items = []  # type: List[InfoItem]
        self.bottom_action_bar = ActionBar(css_class="margin-top-sm")  # 底部的操作栏

    def add_item(self, item: InfoItem) -> None:
        item.index = len(self.items)
        self.items.append(item)

    @property
    def item_groups(self) -> List[List[InfoItem]]:
        return group(self.items, self.cols//2)  # type: ignore

    def render(self) -> bytes:
        padding_count = (len(self.items) * 2) % self.cols
        for i in range(padding_count//2):
            self.add_item(InfoItem())

        return xtemplate.render("common/table/info_table.html", info_table = self)
