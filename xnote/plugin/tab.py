# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-05-12 13:14:25
@LastEditors  : xupingmao
@LastEditTime : 2024-05-13 00:38:36
@FilePath     : /xnote/xnote/plugin/tab.py
@Description  : tab选项卡组件
"""
from xnote.core import xtemplate

class TabBox:
    
    TAB_HTML = """
<div class="x-tab-box {{css_class}}" data-tab-key="{{tab_key}}" data-tab-default="{{tab_default}}">
{% if title %}
    <span class="x-tab title">{{title}}</span>
{% end %}
{% for item in tab_list %}
    <a class="x-tab" 
        {% if item.href != "" %} href="{{item.href}}" {% end %}
        data-tab-value="{{item.value}}">{{item.title}}</a>
{% end %}
</div>
"""
    _compiled_template = xtemplate.compile_template(TAB_HTML, "xnote.plugin.tab")

    def __init__(self, tab_key="tab", tab_default="", title = "", css_class=""):
        self.tab_key = tab_key
        self.tab_default = tab_default
        self.css_class = css_class
        self.title = title
        self.tab_list = [] # type: list[TabItem]
    
    def add_tab(self, title="", value="", href=""):
        item = TabItem(title=title, value=value, href=href)
        self.tab_list.append(item)

    def render(self):
        return self._compiled_template.generate(
            css_class=self.css_class, 
            tab_key=self.tab_key,
            tab_default=self.tab_default,
            title=self.title,
            tab_list=self.tab_list)


class TabItem:
    def __init__(self, title="", value="", href=""):
        self.title = title
        self.value = value
        self.href = href



