import typing

from typing import List
from xutils.textutil import safe_str

MAX_DEPTH = 50

class BaseComponent:
    """UI组件的基类"""
    _depth = 0
    
    def render(self) -> str:
        return ""

class BaseContainer(BaseComponent):
    def __init__(self, css_class="", css_style="", html = ""):
        self.css_class = css_class
        self.css_style = css_style
        self.children: List[BaseComponent] = []
        self.html = html

    def add(self, item: BaseComponent):
        self.children.append(item)
        return self

    def set_children(self, children: List[BaseComponent]):
        self.children = children

    def is_empty(self):
        return len(self.children) == 0 and self.html == ""

    def render(self) -> str:
        if self.is_empty():
            return ""
        css_style_attr = ""
        if self.css_style:
            css_style_attr = f'style="{self.css_style}"'
        out = []
        out.append(f"""<div class="{self.css_class}" {css_style_attr}>""")
        out.append(self.html)
        for item in self.children:
            item._depth += 1
            if item._depth > MAX_DEPTH:
                raise Exception(f"render: too deep depth {item._depth}")
            
            item_html = safe_str(item.render())
            out.append(item_html)
        out.append("""</div>""")
        return "".join(out)

Div = BaseContainer
