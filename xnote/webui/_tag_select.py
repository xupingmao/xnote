# -*- coding:utf-8 -*-
"""通用的 tag 风格选择器组件（可独立于 ListView / Form 使用）。

渲染结构兼容 x-tag-select.js 的 initTagSelect（复用统一的选中态与值同步逻辑）。
容器使用规范 class `.tag-select`，与表单的 `.form-tag-select`、列表行的 `.list-tag-select` 共享同一套 JS 交互。
"""
import typing

from .base import BaseComponent
from xnote.core import xtemplate


class _TagSelectOption:
    """TagSelect 的选项"""

    def __init__(self, title="", value=""):
        self.title = title
        self.value = value


class TagSelect(BaseComponent):
    """通用的 tag 风格选择器（点选标签，单选/多选，提交逗号分隔值）。

    可独立使用，不依赖 ListView / Form。选项通过 add_option(title, value) 添加，
    用法与 DataForm.add_tag_select 一致：
        ts = TagSelect(text="状态", name="status", value="1")
        ts.add_option("进行中", "1").add_option("已完成", "2")
    单选默认只选中一个；多选传 multiple=True，提交值为逗号分隔的多个值。
    """

    _code = xtemplate.compile_template("""
<div class="{{item.css_class}} tag-select" data-multiple="{{'true' if item.multiple else 'false'}}" {% if item.readonly %}data-readonly="1"{% end %}{% if item.data_type %} data-type="{{item.data_type}}"{% end %}{% if item.data_p %} data-p="{{item.data_p}}"{% end %}>

{% if item.icon_class %}
    <i class="{{item.icon_class}}"></i>
{% end %}

{% if item.text %}
    <span class="tag-select-label">{{ item.text }}</span>
{% end %}

    <input type="hidden" name="{{item.name}}" class="form-row-value" value="{{item.value}}">

{% for option in item.options %}
    <span class="tag lightblue {% if option.value in item.selected_values %}active{% end %}" data-value="{{option.value}}">{{option.title}}</span>
{% end %}

</div>
""")

    multiple = False
    readonly = False
    icon_class = ""
    css_class = ""
    data_type = ""
    data_p = ""

    def __init__(self, text="", name="", value="", multiple=False, readonly=False, css_class="", data_type="", data_p=""):
        self.text = text
        self.name = name
        self.value = self._format_value(value)
        self.selected_values = self._normalize_value(value)
        self.multiple = multiple
        self.readonly = readonly
        self.css_class = css_class
        self.icon_class = ""
        self.data_type = data_type
        self.data_p = data_p
        self.options = []

    def add_option(self, title="", value=""):
        self.options.append(_TagSelectOption(title=title, value=value))
        return self

    def _format_value(self, value):
        if isinstance(value, list):
            return ",".join([str(v) for v in value])
        if value is None:
            return ""
        return str(value)

    def _normalize_value(self, value):
        """把 value（逗号分隔字符串或列表）归一化为值列表"""
        if value is None:
            return []
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        if isinstance(value, list):
            return [str(v) for v in value]
        return [str(value)]

    def render(self):
        return self._code.generate(item = self)
