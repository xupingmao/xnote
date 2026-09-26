# encoding=utf-8
# 演示(example)功能的公共导航 tab 组件，供各 demo 子页面复用。
from xnote.plugin import TabBox


def get_example_tab(tab_default=""):
    """构建演示功能左侧的导航 tab 栏，每个 tab 对应一个独立的演示页面/文件。

    tab 的 href 统一指向 /examples/<name>。xmanager 只要求 URL 以模块路径开头
    （xnote_handlers/examples/<file> 的模块路径是 /examples），不需要、也不应该
    再多包一层 /examples/example/<name>。
    """
    tab = TabBox(tab_key="name", title="案例:", css_class="btn-style", tab_default=tab_default)
    tab.add_tab("文本示例", value="text", href="/examples/text")
    tab.add_tab("按钮示例", value="btn", href="/examples/btn")
    tab.add_tab("Tab示例", value="tab", href="/examples/tab")
    tab.add_tab("Tag示例", value="tag", href="/examples/tag")
    tab.add_tab("Switch示例", value="switch", href="/examples/switch")
    tab.add_tab("Form示例", value="form", href="/examples/form")
    tab.add_tab("Dialog示例", value="dialog", href="/examples/dialog")
    tab.add_tab("Dropdown示例", value="dropdown", href="/examples/dropdown")
    tab.add_tab("Table示例", value="table", href="/examples/table")
    tab.add_tab("ListView示例", value="list_view", href="/examples/list_view")
    tab.add_tab("ListPlugin", value="list_plugin", href="/examples/list_plugin")
    tab.add_tab("路由插件", value="router", href="/examples/router")
    tab.add_tab("Tree示例", value="tree", href="/examples/tree")
    tab.add_tab("日历组件", value="calendar", href="/examples/calendar")
    tab.add_tab("Hammer示例", value="hammer", href="/examples/hammer")
    return tab
