from xnote.plugin.base import BaseComponent, BaseContainer
from xnote.plugin.component import TextSpan, EditFormButton, ConfirmButton

class ActionBar(BaseContainer):
    """表格动作栏"""
    def __init__(self, css_class=""):
        super().__init__(css_class=f"action-bar {css_class}")
        self.right_box = BaseContainer("float-right")
        self.add(self.right_box)

    def is_empty(self):
        return len(self.right_box.children) == 0 and len(self.children) == 1

    def _add(self, item: BaseComponent, float_right=False):
        if float_right:
            self.right_box.add(item)
        else:
            self.add(item)

    def add_span(self, text="", css_class="", float_right=False):
        span = TextSpan(text=text, css_class=css_class)
        self._add(span, float_right)

    def add_edit_button(self, text="", url="", css_class="", float_right=False):
        btn = EditFormButton(text = text, url = url, css_class=css_class)
        self._add(btn, float_right)

    def add_confirm_button(self, text="", url="", message="", css_class="", method="GET", reload_url="", float_right=False):
        btn = ConfirmButton(text=text, url=url, message=message, method=method, reload_url=reload_url, css_class=css_class)
        self._add(btn, float_right)
