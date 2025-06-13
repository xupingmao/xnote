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
from xnote.core import xconfig

class TabBox:
    
    TAB_HTML = """
<div class="x-tab-box {{css_class}}" data-tab-key="{{tab_key}}" data-tab-default="{{tab_default}}">
{% if title %}
    <span class="x-tab title">{{title}}</span>
{% end %}
{% for item in tab_list %}
    <a class="x-tab {{item.css_class}}" 
        {% if item.href != "" %} href="{{item.href}}" {% end %}
        {% if item.onclick != "" %} onclick="{{item.onclick}}" {% end %}
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
    
    def add_item(self, title="", value="", href="", css_class="", onclick="", item_id=""):
        item = TabItem(title=title, value=value, href=href, css_class=css_class, onclick=onclick, item_id=item_id)

        if len(item_id) > 0:
            for item in self.tab_list:
                if item.item_id == item_id:
                    # 已经存在
                    return

        self.tab_list.append(item)

    add_tab = add_item

    def render(self):
        return self._compiled_template.generate(
            css_class=self.css_class, 
            tab_key=self.tab_key,
            tab_default=self.tab_default,
            title=self.title,
            tab_list=self.tab_list)


class TabItem:
    def __init__(self, title="", value="", href="", css_class="", onclick="", item_id=""):
        href = xconfig.WebConfig.resolve_path(href)
        self.title = title
        self.value = value
        self.href = href
        self.css_class = css_class
        self.onclick = onclick
        self.item_id = item_id


class TabConfig:

    # 编解码工具
    codecs_tab = TabBox(tab_key="tab", tab_default="base64", css_class="btn-style")
    codecs_tab.add_item(title="BASE64", value="base64", href="/tools/base64?tab=base64")
    codecs_tab.add_item(title="16进制转换", value="hex", href="/tools/hex?tab=hex")
    codecs_tab.add_item(title="URL编解码", value="urlcoder", href="/tools/urlcoder?tab=urlcoder")
    codecs_tab.add_item(title="MD5", value="md5", href="/tools/md5?tab=md5")
    codecs_tab.add_item(title="SHA1", value="sha1", href="/tools/sha1?tab=sha1")
    codecs_tab.add_item(title="条形码", value="barcode", href="/tools/barcode?tab=barcode")
    codecs_tab.add_item(title="二维码", value="qrcode", href="/tools/qrcode?tab=qrcode")


    # 图片工具
    img_tab = TabBox(tab_key="tab", tab_default="img_split", css_class="btn-style")