from xnote.webui.base import BaseComponent, BaseContainer, Div
from xnote.webui.component import TextSpan, EditFormButton, ConfirmButton, TextLink
from xnote.webui.component import TextItemSep, TextNbsp, TextBr
from xnote.core import xtemplate
from typing import Optional

class TextContainer(BaseContainer):
    
    def add_span(self, text="", css_class="", css_style="", id=""):
        self.children.append(TextSpan(text=text, css_class=css_class, css_style=css_style, id=id))
    
    def add_link(self, text="", href="", css_class="", is_bracketed=False):
        self.children.append(TextLink(text=text, href=href, css_class=css_class, is_bracketed=is_bracketed))
    
    def add_br(self, count=1):
        for _ in range(count):
            self.children.append(TextBr())
        
    def add_nbsp(self, count=1):
        for _ in range(count):
            self.children.append(TextNbsp())
    
    def add_item_sep(self):
        self.children.append(TextItemSep())

class ActionBar(TextContainer):
    """操作栏"""
    def __init__(self, css_class="", css_style=""):
        super().__init__(css_class=f"action-bar {css_class}", css_style=css_style)
        self.extra = TextContainer("row-extra")
        self.add(self.extra)

    @property
    def right_div(self):
        return self.extra

    def is_empty(self):
        return len(self.extra.children) == 0 and len(self.children) == 1
    
    @property
    def visible(self):
        return not self.is_empty()

    def _add(self, item: BaseComponent, float_right=False):
        if float_right:
            self.extra.add(item)
        else:
            self.add(item)

    def add_right(self, item: BaseComponent):
        self.extra.add(item)

    def add_span(self, text="", css_class="", float_right=False, id=""):
        span = TextSpan(text=text, css_class=css_class, id=id)
        self._add(span, float_right)

    def add_edit_button(self, text="", url="", css_class="", float_right=False):
        btn = EditFormButton(text = text, url = url, css_class=css_class)
        self._add(btn, float_right)

    def add_confirm_button(self, text="", url="", message="", css_class="", method="GET", reload_url="", float_right=False, is_alert=False):
        btn = ConfirmButton(text=text, url=url, message=message, method=method, reload_url=reload_url, css_class=css_class, is_alert=is_alert)
        self._add(btn, float_right)

    def add_link(self, text = "", href="", css_class="", float_right=False):
        link = TextLink(text=text, href=href, css_class=css_class)
        self._add(link, float_right)
    
    def add_nbsp(self, count=1):
        for _ in range(count):
            self.children.append(TextNbsp())
            
    def add_item_sep(self):
        self.children.append(TextItemSep())
        

class Card(BaseContainer):
    """卡片容器，一个卡片可以包含多个行"""
    def __init__(self, css_class="") -> None:
        super().__init__(css_class="card " + css_class)


class RowPanel(TextContainer):
    """行面板容器"""
    def __init__(self, css_class="") -> None:
        super().__init__(css_class="row " + css_class)
        self.extra = TextContainer("row-extra")
        self.add(self.extra)

class RowDiv(RowPanel):
    """行容器"""
    
    @property
    def right_div(self):
        # deprecated: 请使用 extra 替代
        return self.extra

CardRow = RowDiv
