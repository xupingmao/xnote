
class BaseComponent:
    """UI组件的基类"""
    def render(self):
        return ""


class BaseContainer(BaseComponent):
    def __init__(self, css_class=""):
        self.css_class = css_class
        self.children = [] # type: list[BaseComponent]

    def add(self, item: BaseComponent):
        self.children.append(item)

    def is_empty(self):
        return len(self.children) == 0

    def render(self):
        if self.is_empty():
            return ""
        out = []
        out.append(f"""<div class="{self.css_class}">""")
        for item in self.children:
            out.append(item.render())
        out.append("""</div>""")
        return "".join(out)
