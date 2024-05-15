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
<div class="x-tab-box {{css_class}}">
{% for item in {{tab_list}}} %}
    <a class="x-tab" 
        {% if item.href != "" %} href="{{item.href}}" {% end %}
        data-tab-value="{{item.value}}">{{item.title}}</a>
{% end %}
</div>
"""
    _compiled_template = xtemplate.compile_template(TAB_HTML, "<tab-template>")

    def __init__(self, css_class=""):
        self.css_class = css_class
        self.tab_list = []
    
    def add_tab(self, title="", value="", href=""):
        item = TabItem(title=title, value=value, href=href)
        self.tab_list.append(item)

    def render(self):
        return self._compiled_template.generate(css_class=self.css_class, tab_list=self.tab_list)


class TabItem:
    def __init__(self, title="", value="", href=""):
        self.title = title
        self.value = value
        self.href = href



