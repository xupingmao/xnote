from typing import Optional
from xutils import escape_html
from .base import BaseComponent
from .utils import build_data_attrs, get_first_valid_arg

class TextLink(BaseComponent):
    """文本链接"""
    def __init__(self, text="", href="", css_class="", is_bracketed=False):
        self.text = text
        self.href = href
        self.css_class = css_class
        self.is_bracketed = is_bracketed
        
    def _render(self):
        text = escape_html(self.text)
        href = self.href
        if self.css_class:
            return f"""<a href="{href}" class="{self.css_class}">{text}</a>"""
        else:
            return f"""<a href="{href}">{text}</a>"""

    def render(self):
        html = self._render()
        if self.is_bracketed:
            return f"[{html}]"
        return html

class ActionLink(TextLink):
    """操作链接"""
    def __init__(self, text="", href="", css_class="", onclick="", data_dict:Optional[dict] = None):
        self.text = text
        self.href = href
        self.css_class = css_class
        self.onclick = onclick
        self.data_dict = data_dict
        
    def render(self):
        text = escape_html(self.text)
        data_attrs = build_data_attrs(self.data_dict)
        href_attr = ""
        if self.href:
            href_attr = f'href="{self.href}"'
        
        onclick_attr = ""
        if self.onclick:
            onclick_attr = f'onclick="{self.onclick}"'

        return f"""
[<a class="{self.css_class}" {onclick_attr} {href_attr} {data_attrs}>{text}</a>]
"""

class EditFormActionLink(ActionLink):
    """编辑表单的链接"""
    def __init__(self, text = "", url = "", css_class=""):
        data_dict = dict(url = url, title = text)
        super().__init__(text = text, css_class=css_class, onclick="xnote.table.handleEditForm(this)", data_dict=data_dict)


class ConfirmActionLink(ActionLink):
    """确认操作链接"""
    def __init__(self, text = "", url = "", message = "", msg: Optional[str] = None, css_class=""):
        msg = get_first_valid_arg(msg, message)
        data_dict = dict(url = url, msg=msg)
        super().__init__(text = text, css_class=css_class, onclick="xnote.table.handleConfirmAction(this)", data_dict=data_dict)
