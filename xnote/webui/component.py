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

import warnings
from typing import Optional, Union
from xnote.webui.base import BaseComponent, BaseContainer
from xnote.core import xtemplate
from xutils import escape_html
from .link import TextLink, EditFormActionLink
from .utils import build_attrs
from xutils import jsonutil

class RawHtml(BaseComponent):
    def __init__(self, html: Union[str, bytes]) -> None:
        self.html = html
        
    def render(self):
        return self.html

class Panel(BaseContainer):

    def __init__(self, css_class=""):
        super().__init__(css_class=f"row x-plugin-panel {css_class}")

class Input(BaseComponent):
    """输入控件

    除了固定的几个参数, 其余**原生属性**通过关键字参数透传, 这样 `accept` /
    `pattern` / `maxlength` 这类 HTML 原生能力不用再靠手写 `<input>` 绕开组件:

        Input(type="file", name="file", accept=".csv")
        Input(name="age", type="number", min="0", max="120")

    ⚠ 关键字里的下划线会转成短横线(`data_role` -> `data-role`), 因为 Python 的
    关键字参数名不允许出现短横线。
    """

    def __init__(self, type = "text", name = "", css_class="", value="", id="", placeholder="",
                 accept = "", pattern = "", maxlength = "", minlength = "",
                 readonly = False, **extra_attrs) -> None:
        self.name = name
        self.type = type
        self.css_class = css_class
        self.value = value
        self.id = id
        self.placeholder = placeholder
        self.accept = accept
        self.pattern = pattern
        self.maxlength = maxlength
        self.minlength = minlength
        self.readonly = readonly
        self.extra_attrs = extra_attrs

    def render(self) -> str:
        attr_dict = {
            "name": self.name,
            "class": self.css_class,
            "type": self.type,
            "value": self.value,
            "accept": self.accept,
            "pattern": self.pattern,
            "maxlength": self.maxlength,
            "minlength": self.minlength,
        }
        if self.id:
            attr_dict["id"] = self.id
        if self.placeholder:
            attr_dict["placeholder"] = self.placeholder
        if self.readonly:
            attr_dict["readonly"] = "readonly"
        # 其余原生属性原样透传(下划线转短横线)
        for key, value in self.extra_attrs.items():
            attr_dict[key.replace("_", "-")] = value
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


class SubmitButton(BaseComponent):
    """TODO 待优化
    
    原生提交按钮 `<button type="submit">`

    ⚠ `form` 参数是给"按钮不在 `<form>` 里面"的场景用的: `DataForm` 的 footer 渲染在
    `</form>` **之后**(见 `common/form/form.html`), 那里放 `<button type="submit">`
    是点不动的。HTML5 的 `form="<表单的 DOM id>"` 正好解决这件事 —— 不写 JS,
    按钮照样提交指定的表单, 浏览器原生支持。
    """

    def __init__(self, text="提交", css_class="btn", form="", id="", name=""):
        self.text = text
        self.css_class = css_class
        self.form = form
        self.id = id
        self.name = name

    def render(self):
        attr_dict = {
            "type": "submit",
            "class": self.css_class,
            "id": self.id,
            "name": self.name,
            "form": self.form,
        }
        attr_list = build_attrs(attr_dict)
        text = escape_html(self.text)
        return f"<button {attr_list}>{text}</button>"


class ActionButton(BaseComponent):
    """查询后的操作行为按钮，不需要确认就能安全执行的, 比如刷新等"""

    def __init__(self, *, text="", onclick="xnote.plugin.onClick(this)", url="", 
                 css_class="btn",  css_style = "",
                 id="", name="", type="",
                 data_names = "", data_params:Optional[dict] = None, 
                 confirm_msg = "", prompt_msg = "", prompt_value = "",
                 extra_data_attrs:Optional[dict] = None) -> None:
        """
        :param id: 按钮本身的id
        :param name: 按钮本身的name
        :param data_names: 需要提交数据的names列表, {*}表示所有参数, 为空或{_}表示无参数, {arg1,arg2} 指定参数
        :param confirm_msg: 如果需要用户确认, 通过这个参数设置确认信息.
        :param prompt_msg: 如果需要用户输入，通过这个参数来设置
        :param prompt_value: 输入框的默认值, 配合 prompt_msg 使用
        :param extra_data_attrs: 额外的 data-* 属性(dict), key 中的下划线会转成短横线,
                                 例如 {"data_key": "x"} 渲染为 data-key="x", 供页面自定义 JS 读取.
        """
        self.text = text
        self.onclick = onclick
        self.css_class = css_class
        self.css_style = css_style
        self.id = id
        self.name = name
        self.type = type
        self.data_names = data_names
        self.data_params = data_params
        self.url = url
        self.confirm_msg = confirm_msg
        self.prompt_msg = prompt_msg
        self.prompt_value = prompt_value
        self.extra_data_attrs = extra_data_attrs or {}
    
    def render(self):
        data_params_json = ""
        if self.data_params:
            data_params_json = jsonutil.tojson(self.data_params)
            
        attr_dict = {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "class": self.css_class,
            "style": self.css_style,
            "onclick": self.onclick,
            "data-url": self.url,
            "data-names": self.data_names,
            "data-params": data_params_json,
            "data-confirm-msg": escape_html(self.confirm_msg),
            "data-prompt-msg": escape_html(self.prompt_msg),
            "data-prompt-value": escape_html(self.prompt_value),
        }
        for key, value in self.extra_data_attrs.items():
            # 形如 {"data_key": "x"} -> data-key="x"
            attr_dict[key.replace("_", "-")] = escape_html(str(value))
        attr_list = build_attrs(attr_dict)
        text = escape_html(self.text)
        return f"<button {attr_list}>{text}</button>\n"

# 别名
AjaxButton = ActionButton

class ConfirmButton(ActionButton):
    """
    .. deprecated:: 1.2.0
        新接入请使用 `ActionButton` 的 `confirm_msg` 参数, 此处为兼容旧代码保留
        
    确认按钮
    """
    def __init__(self, text="", url="", message="确认执行吗?", method="GET", reload_url="", css_class="", css_style="", is_alert=False, id=""):
        warnings.warn("使用 `ActionButton` 的 `confirm_msg` 参数, 此处兼容旧代码保留")
        self.id = id
        self.text = text
        self.url = url
        self.method = method
        self.css_class = css_class
        self.css_style = css_style
        self.message = message
        self.reload_url = reload_url
        self.is_alert = is_alert

    def render(self):
        text = escape_html(self.text)
        is_alert_attr = ""
        if self.is_alert:
            is_alert_attr = "1"
            
        attr_dict = {
            "id": self.id,
            "class": f"btn {self.css_class}",
            "style": self.css_style,
            "onclick": "xnote.table.handleConfirmAction(this, event)",
            "data-url": self.url,
            "data-msg": escape_html(self.message),
            "data-method": self.method,
            "data-is-alert": is_alert_attr,
            "data-reload-url": self.reload_url,
        }
        attr_list = build_attrs(attr_dict)
        return f"<button {attr_list}>{text}</button>\n"

class PromptButton:
    """询问输入按钮"""
    def __init__(self, text, action, context=None):
        pass

class EditFormButton(BaseComponent):
    """编辑表单的按钮"""
    def __init__(self, text = "", url = "", css_class="", css_style=""):
        self.text = text
        self.url = url
        self.css_class = css_class
        self.css_style = css_style

    def render(self):
        text = escape_html(self.text)
        # 首尾不要带换行: 被包进 <span> 时浏览器会渲染成空格, 撑开按钮间距
        attr_dict = {
            "style": self.css_style,
            "class": f"btn {self.css_class}",
            "onclick": "xnote.table.handleEditForm(this)",
            "data-url": self.url,
            "data-title": text,
        }
        attr_list = build_attrs(attr_dict)
        return f'<button {attr_list}>{text}</button>'


class TextBase(BaseComponent):
    """文本基类"""
    
    tag_name = "span"
    
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
        tag_name = self.tag_name
        
        return f"""<{tag_name} {attr_list}>{text}</{tag_name}>"""

class TextSpan(TextBase):
    """行内文本"""
    tag_name = "span"
    
class TextPre(TextBase):
    """格式化文本"""
    tag_name = "pre"
    

class Icon(BaseComponent):
    """行内图标，渲染为 <i class="{icon_class}"></i>（如 font-awesome 的 fa fa-file-text-o）"""
    def __init__(self, icon_class="", css_class="", css_style="", id=""):
        self.icon_class = icon_class
        self.css_class = css_class
        self.css_style = css_style
        self.id = id

    def render(self):
        attr_dict = {
            "id": self.id,
            "style": self.css_style,
            "class": (self.icon_class + " " + self.css_class).strip(),
        }
        attr_list = build_attrs(attr_dict)
        return f"""<i {attr_list}></i>"""

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
    def __init__(self, text="", css_class="", href="", active=False):
        self.text = text
        self.css_class = css_class
        self.href = href
        self.active = active

    def render(self):
        text = escape_html(self.text)
        css_class = self.css_class
        if self.active:
            css_class = (css_class + " active").strip()
        if self.href:
            return f"""<span class="tag {css_class}"><a href="{self.href}">{text}</a></span>"""
        return f"""<span class="tag {css_class}">{text}</span>"""
    
class DropdownOption(BaseComponent):
    def __init__(self, name="", value=""):
        self.name = name
        self.value = value

    def render(self):
        return f'<option value="{self.value}">{self.name}</option>'
    
class Dropdown(BaseContainer):
    _template = xtemplate.compile_template("""
<select>
    {% for option in item.children %}
        {% render option %}
    {% end %}
</select>
""", name="xnote.plugin.dropdown")
    

    def __init__(self):
        super().__init__()

    def add_option(self, name="", value=""):
        self.children.append(DropdownOption(name=name, value=value))

    def render(self):
        return self._template.generate(item=self)


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
