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

class UIComponent:
    """UI组件的基类"""
    def render(self):
        return ""

class Panel(UIComponent):

    def __init__(self):
        self.children = []

    def add(self, child):
        self.children.append(child)

    def render(self):
        html = '<div class="row x-plugin-panel">'
        for child in self.children:
            html += child.render()
        html += '</div>'
        return html


class Input(UIComponent):
    """输入文本框"""

    def __init__(self, label, name, value):
        self.label = label
        self.name = name
        self.value = value

    def render(self):
        html = '<div class="x-plugin-input">'
        html += '<label class="x-plugin-input-label">%s</label>' % self.label
        html += '<input class="x-plugin-input-text" name="%s" value="%s">' % (
            self.name, self.value)
        html += '</div>'
        return html


class Textarea:

    def __init__(self, label, name, value):
        pass


class TabLink:
    """tab页链接"""

    def __init__(self):
        pass


class SubmitButton:
    """提交按钮"""

    def __init__(self, label):
        pass


class ActionButton:
    """查询后的操作行为按钮，比如删除、刷新等"""

    def __init__(self, label, action, context=None):
        pass


class ConfirmButton:
    """确认按钮"""

    def __init__(self, label, action, context=None):
        pass


class PromptButton:
    """询问输入按钮"""

    def __init__(self, label, action, context=None):
        pass