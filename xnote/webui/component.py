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

from typing import Optional
from xnote.webui.base import BaseComponent, BaseContainer
from xnote.core import xtemplate
from xutils import escape_html
from .link import TextLink, EditFormActionLink
from .utils import build_attrs
from xutils import jsonutil

class RawHtml(BaseComponent):
    def __init__(self, html: str) -> None:
        self.html = html
        
    def render(self):
        return self.html

class Panel(BaseContainer):

    def __init__(self, css_class=""):
        super().__init__(css_class=f"row x-plugin-panel {css_class}")

class Input(BaseComponent):
    def __init__(self, type = "text", name = "", css_class="", value="") -> None:
        self.name = name
        self.type = type
        self.css_class = css_class
        self.value = value
        
    def render(self) -> str:
        attr_dict = {
            "name": self.name,
            "class": self.css_class,
            "type": self.type,
            "value": self.value,
        }
        attr_list = build_attrs(attr_dict)
        return f"<input {attr_list}>"

class InputGroup(BaseComponent):
    """输入文本框"""

    def __init__(self, label: str, name: str, value: str, css_class="", readonly=False, type="text"):
        self.label = label
        self.name = name
        self.value = value
        self.css_class = css_class
        self.readonly = readonly
        self.type = type

    def render(self):
        label = escape_html(self.label)
        name = escape_html(self.name)
        value = escape_html(self.value)
        input_attr_list = ""
        if self.readonly:
            input_attr_list += " readonly"
            
        return f"""
<div class="input-group {self.css_class}">
    <label>{label}</label>
    <input name="{name}" type="{self.type}" value="{value}" {input_attr_list}>
</div>
"""
    
    


class Textarea(BaseComponent):
    def __init__(self, value: str, name = "", placeholder = "", rows = "", cols = "", css_class="", label = ""):
        self.name = name
        self.value = value
        self.placeholder = placeholder
        # TODO 待实现
        self.label = label
        self.rows = rows
        self.cols = cols
        self.css_class = css_class
    
    def render(self):
        attr_dict = {}
        if self.name:
            attr_dict["name"] = self.name
        if self.placeholder:
            attr_dict["placeholder"] = self.placeholder
        if self.rows:
            attr_dict["rows"] = self.rows
        if self.cols:
            attr_dict["cols"] = self.cols
        if self.css_class:
            attr_dict["class"] = self.css_class
            
        attrs = build_attrs(attr_dict)
        value = escape_html(self.value, escape_blank=False)
        return f"""<textarea {attrs}>{value}</textarea>"""
    
class Checkbox(BaseComponent):
    def __init__(self, name = "", text="", checked = "", id="") -> None:
        self.checked = checked
        self.name = name
        self.text = text
        self.id = id
        
    def render(self):
        text_span = ""
        if self.text:
            text_span = f"<span>{escape_html(self.text)}</span>"
        return f"""
<label class="checkbox-item">
    <input type="checkbox" name="{self.name}" {self.checked}>
    {text_span}
</label>
"""

class TabLink:
    """tab页链接"""

    def __init__(self):
        pass


class SubmitButton:
    """提交按钮"""

    def __init__(self, text):
        pass


class ActionButton(BaseComponent):
    """查询后的操作行为按钮，不需要确认就能安全执行的, 比如刷新等"""

    def __init__(self, text="", onclick="xnote.plugin.onClick(this)", css_class="btn", id="", name="",
                 data_names = "", data_params:Optional[dict] = None):
        """
        :param id: 按钮本身的id
        :param name: 按钮本身的name
        :param data_names: 需要提交数据的names列表, {*}或者为空表示所有参数, {_}表示无参数, {arg1,arg2} 指定参数
        """
        self.text = text
        self.onclick = onclick
        self.css_class = css_class
        self.id = id
        self.name = name
        self.data_names = data_names
        self.data_params = data_params
    
    def render(self):
        data_params_json = ""
        if self.data_params:
            data_params_json = jsonutil.tojson(self.data_params)
            
        attr_dict = {
            "id": self.id,
            "name": self.name,
            "class": self.css_class,
            "onclick": self.onclick,
            "data-names": self.data_names,
            "data-params": data_params_json,
        }
        attr_list = build_attrs(attr_dict)
        text = escape_html(self.text)
        return f"<button {attr_list}>{text}</button>\n"


class ConfirmButton(ActionButton):
    """确认按钮"""
    def __init__(self, text="", url="", message="确认执行吗?", method="GET", reload_url="", css_class="", is_alert=False):
        self.text = text
        self.url = url
        self.method = method
        self.css_class = css_class
        self.message = message
        self.reload_url = reload_url
        self.is_alert = is_alert

    def render(self):
        text = escape_html(self.text)
        message = escape_html(self.message)
        css_class = self.css_class
        url = self.url
        method = self.method
        reload_url = self.reload_url
        
        is_alert_attr = ""
        if self.is_alert:
            is_alert_attr = "data-is-alert=1"
            
        return f"""<button class="btn {css_class}" onclick="xnote.table.handleConfirmAction(this, event)" {is_alert_attr}
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

class TextSpan(BaseComponent):
    """行内文本"""
    def __init__(self, text="", css_class="", css_style="", id=""):
        self.text = text
        self.css_class = css_class
        self.css_style = css_style
        self.id = id

    def render(self):
        text = escape_html(self.text)
        attr_dict = {
            "id": self.id,
            "style": self.css_style,
            "class": self.css_class,
        }
        attr_list = build_attrs(attr_dict)
        return f"""<span {attr_list}>{text}</span>"""

class TagSpan(BaseComponent):
    def __init__(self, text="", href="", css_class="", badge_info="", icon_class="", text_html=""):
        self.text = text
        self.text_html = text_html
        self.href = href
        self.css_class = css_class
        self.badge_info = badge_info
        self.icon_class = icon_class

    def render(self):
        if self.text_html:
            text = self.text_html
        else:
            text = escape_html(self.text)
        
        icon_html = ""
        if self.icon_class:
            icon_html = f"""<i class="{self.icon_class}"></i>"""
        return f"""
<span class="tag-span {self.css_class}">
    {icon_html}
    <a class="tag-link" href="{self.href}">{text}</a>
    {self.badge_info}
</span>"""

class TextTag(BaseComponent):
    def __init__(self, text="", css_class="", href=""):
        self.text = text
        self.css_class = css_class
        self.href = href
    
    def render(self):
        text = escape_html(self.text)
        if self.href:
            return f"""<span class="tag {self.css_class}"><a href="{self.href}">{text}</a></span>"""
        return f"""<span class="tag {self.css_class}">{text}</span>"""
    
class DropdownOption(BaseComponent):
    def __init__(self, name="", value=""):
        self.name = name
        self.value = value
    
class Dropdown(BaseContainer):
    _template = xtemplate.compile_template("""
<select>
    {% for item in self.chidren %}
        {% render item %}
    {% end %}
</select>
""", name="xnote.plugin.dropdown")
    

    def __init__(self):
        pass

    def add_option(self, name="", value=""):
        self.children.append(DropdownOption(name=name, value=value))

    def render(self):
        return self._template.generate(children = self.children)


class BlockTitle(BaseComponent):
    _code = """
<div class="block-title">
    <span>{{item.text}}</span>
</div>
"""
    _template = xtemplate.compile_template(_code, "xnote.plugin.blocktitle")

    def __init__(self, text = ""):
        self.text = text

    def render(self):
        if self.text == "":
            return ""
        return self._template.generate(item = self)

class TextBr(BaseComponent):
    def render(self):
        return "<br>"

class TextNbsp(BaseComponent):
    def render(self) -> str:
        return "&nbsp;"

class TextItemSep(BaseComponent):
    def render(self) -> str:
        # return " · "
        return " | "
