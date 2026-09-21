# -*- coding:utf-8 -*-
"""通用的开关组件（Switch）。

渲染结构兼容 x-switch.js 的 initSwitch（点击切换选中态并同步隐藏域的值）。
与 TagSelect 保持一致的交互契约：隐藏域是值的唯一来源，选中态（active类）只用于展示。
这样开关可以直接放进普通表单 / DataForm 里提交：DataForm 的 formData() 取的是
`.val()`，用隐藏域能保证取到当前开关状态（原生 checkbox 的 val() 恒为 value，
无法表达未选中）。

用法:
    sw = Switch(name="enabled", text="启用", checked=True)
"""
from typing import Any

from .base import BaseComponent
from xnote.core import xtemplate

# 可识别为"开"的文本值，便于直接把数据库里的字符串值传回 checked 参数
TRUE_TEXTS = ("true", "1", "on", "yes")


class Switch(BaseComponent):
    """开关组件（开/关二态）

    用法:
        sw = Switch(name="enabled", text="启用", checked=True)

    参数:
        name:      表单字段名（渲染为隐藏域的 name）
        text:      开关右侧的说明文字，为空则不渲染
        checked:   是否选中，支持 bool 或字符串（"true"/"1"/"on"/"yes" 视为开）
        on_value:  开关打开时提交的值（默认 "true"）
        off_value: 开关关闭时提交的值（默认 "false"）
        disabled:  禁用，点击不生效
        size:      尺寸，可选 "sm" / "lg"，留空为默认尺寸
    """

    _code = xtemplate.compile_template("""
<span class="{{item.full_css_class}}"{% if item.id %} id="{{item.id}}"{% end %} role="switch" tabindex="{{item.tab_index}}" aria-checked="{{'true' if item.checked else 'false'}}" data-on-value="{{item.on_value}}" data-off-value="{{item.off_value}}"{% if item.disabled %} data-disabled="1"{% end %}>
    <input type="hidden" name="{{item.name}}" value="{{item.hidden_value}}">
    <span class="switch-track"><span class="switch-dot"></span></span>
    {% if item.text %}
    <span class="switch-text">{{item.text}}</span>
    {% end %}
</span>
""")

    def __init__(self, name="", text="", checked: Any = False, on_value="true",
                 off_value="false", disabled=False, size="", css_class="", id=""):
        self.name = name
        self.text = text
        self.checked = self._parse_checked(checked)
        self.on_value = str(on_value)
        self.off_value = str(off_value)
        self.disabled = disabled
        self.size = size
        self.css_class = css_class
        self.id = id

    def _parse_checked(self, checked: Any) -> bool:
        """把 bool / 字符串 / 数字归一化为布尔值"""
        if isinstance(checked, bool):
            return checked
        if checked is None:
            return False
        return str(checked).strip().lower() in TRUE_TEXTS

    @property
    def hidden_value(self) -> str:
        """隐藏域的值，是开关提交值的唯一来源"""
        if self.checked:
            return self.on_value
        return self.off_value

    @property
    def tab_index(self) -> str:
        """禁用时不参与键盘 tab 导航"""
        if self.disabled:
            return "-1"
        return "0"

    @property
    def full_css_class(self) -> str:
        parts = ["x-switch"]
        if self.size:
            parts.append(f"switch-{self.size}")
        if self.checked:
            parts.append("active")
        if self.disabled:
            parts.append("disabled")
        if self.css_class:
            parts.append(self.css_class)
        return " ".join(parts).strip()

    def render(self):
        return self._code.generate(item=self)
