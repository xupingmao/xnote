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
from typing import List
from xnote.core import xtemplate
from xnote.core import xconfig
from xnote.webui.component import BlockTitle
from xnote.webui.base import BaseComponent, BaseContainer

# TODO: 支持多级tab, 例如 tab=dev.text

class TabBox(BaseComponent):
    
    _tab_html_v1 = """
<div class="row x-tab-box {{css_class}}" data-tab-key="{{tab_key}}" data-tab-default="{{tab_default}}">
    {% render block_title %}
    {% if title %}
        <div style="{{title_style}}">
            <span class="x-tab title" >{{title}}</span>
        </div>
    {% end %}

    <div style="{{tabs_style}}">
        {% for item in tab_list %}
            <a class="x-tab {{item.css_class}}" 
                {% if item.href != "" %} href="{{item.href}}" {% end %}
                {% if item.onclick != "" %} onclick="{{item.onclick}}" {% end %}
                data-tab-value="{{item.value}}">{{item.title}}</a>
        {% end %}
    </div>
    
    {% render extra %}
</div>
"""
    _template_v1 = xtemplate.compile_template(_tab_html_v1, "xnote.plugin.tab_v1")

    def __init__(self, tab_key="tab", tab_default="", title = "", css_class="", title_width=""):
        self.tab_key = tab_key
        self.tab_default = tab_default
        self.css_class = css_class
        self.title = title
        self.title_width = title_width
        self.tab_list = [] # type: list[TabItem]
        self.block_title = BlockTitle()
        self._title_style = ""
        self._tabs_style = ""
        self.extra = BaseContainer("float-right")

    @property
    def right_div(self):
        return self.extra
    
    def add_item(self, title="", value="", href="", css_class="", onclick="", item_id=""):
        item = TabItem(title=title, value=value, href=href, css_class=css_class, onclick=onclick, item_id=item_id)

        if len(item_id) > 0:
            for item in self.tab_list:
                if item.item_id == item_id:
                    # 已经存在
                    return

        self.tab_list.append(item)

    add_tab = add_item
    
    def _update(self):
        if self.title_width:
            self._title_style = f"float: left; width: {self.title_width}"
            self._tabs_style = f"float: left; width: calc(100% - {self.title_width})"

    def render(self, tab_value=""):
        tab_default = self.tab_default
        if tab_value != "":
            tab_default = tab_value
        self._update()
        
        return self._template_v1.generate(
            css_class=self.css_class, 
            tab_key=self.tab_key,
            tab_default=tab_default,
            title=self.title,
            tab_list=self.tab_list,
            block_title=self.block_title,
            title_style=self._title_style,
            tabs_style=self._tabs_style,
            extra=self.extra)


class TabItem:
    def __init__(self, title="", value="", href="", css_class="", onclick="", item_id=""):
        href = xconfig.WebConfig.resolve_path(href)
        self.title = title
        self.value = value
        self.href = href
        self.css_class = css_class
        self.onclick = onclick
        self.item_id = item_id


class TabTable(BaseComponent):
    
    _tab_table_html = """
<table class="x-tab-table">
    {% for tab_box in tab_box_list %}
    <tr>
        <td style="{{tab_box._title_style}}">
            <span class="x-tab title">{{tab_box.title}}</span>
        </td>
        <td>
            <div class="x-tab-box {{tab_box.css_class}}" data-tab-key="{{tab_box.tab_key}}" data-tab-default="{{tab_box.tab_default}}">
                {% for item in tab_box.tab_list %}
                <a class="x-tab {{item.css_class}}" 
                    {% if item.href != "" %} href="{{item.href}}" {% end %}
                    {% if item.onclick != "" %} onclick="{{item.onclick}}" {% end %}
                    data-tab-value="{{item.value}}">{{item.title}}</a>
                {% end %}
            </div>
        </td>
    </tr>
    {% end %}
</table>
"""
    
    _tab_table_template = xtemplate.compile_template(_tab_table_html)
    
    def __init__(self) -> None:
        self.children:List[TabBox] = []
        
    def add_tab_box(self, tab_box: TabBox):
        self.children.append(tab_box)
    
    def render(self):
        for tab_box in self.children:
            tab_box._update()
            
        return self._tab_table_template.generate(tab_box_list = self.children)
    