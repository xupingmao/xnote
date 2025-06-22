# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-03-31 11:14:57
@LastEditors  : xupingmao
@LastEditTime : 2024-03-31 11:15:29
@FilePath     : /xnote/xnote/plugin/component.py
@Description  : 描述
"""

from xnote.plugin.base import BaseComponent, BaseContainer
from xnote.core import xtemplate
from xutils import escape_html

class Panel(BaseContainer):

    def __init__(self, css_class=""):
        super().__init__(css_class=f"row x-plugin-panel {css_class}")


class Input(BaseComponent):
    """输入文本框"""

    _template = xtemplate.compile_template("""
<div class="x-plugin-input">
    <label class="x-plugin-input-label">{{info.label}}</label>
    <input class="x-plugin-input-text" name="{{info.name}}" value="{{info.value}}">
</div>
""", name="xnote.plugin.input")

    def __init__(self, label, name, value):
        self.label = label
        self.name = name
        self.value = value

    def render(self):
        return self._template.generate(info = self)


class Textarea:
    def __init__(self, label, name, value):
        self.label = label
        self.name = name
        self.value = value


class TabLink:
    """tab页链接"""

    def __init__(self):
        pass


class SubmitButton:
    """提交按钮"""

    def __init__(self, text):
        pass


class ActionButton:
    """查询后的操作行为按钮，比如删除、刷新等"""

    def __init__(self, text, action, context=None):
        pass


class ConfirmButton(BaseComponent):
    """确认按钮"""
    def __init__(self, text="", url="", message="", method="GET", reload_url="", css_class=""):
        self.text = text
        self.url = url
        self.method = method
        self.css_class = css_class
        self.message = message
        self.reload_url = reload_url

    def render(self):
        text = escape_html(self.text)
        message = escape_html(self.message)
        css_class = self.css_class
        url = self.url
        method = self.method
        reload_url = self.reload_url
        return f"""<button class="btn btn-default {css_class}" onclick="xnote.table.handleConfirmAction(this)" 
        data-url="{url}" data-msg="{message}" data-method="{method}" data-reload-url="{reload_url}">{text}</button>
        """

class PromptButton:
    """询问输入按钮"""
    def __init__(self, text, action, context=None):
        pass

class EditFormButton(BaseComponent):
    """编辑表单的按钮"""
    def __init__(self, text = "", url = "", css_class=""):
        self.text = text
        self.url = url
        self.css_class = css_class

    def render(self):
        text = escape_html(self.text)
        return f"""
<button class="btn {self.css_class}" onclick="xnote.table.handleEditForm(this)"
    data-url="{self.url}" data-title="{text}">{text}</button>
"""

class TextLink(BaseComponent):
    """文本链接"""
    def __init__(self, text="", href=""):
        self.text = text
        self.href = href

    def render(self):
        text = escape_html(self.text)
        href = self.href
        return f"""<a href="{href}">{text}</a>"""


class TextSpan(BaseComponent):
    """行内文本"""
    def __init__(self, text="", css_class=""):
        self.text = text
        self.css_class = css_class

    def render(self):
        text = escape_html(self.text)
        return f"""<span class="{self.css_class}">{text}</span>"""

    