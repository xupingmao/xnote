# encoding=utf-8
# 演示(example)功能的公共导航 tab 组件，供各 demo 子页面复用。
from xnote.plugin import TabBox


def get_example_tab(tab_default=""):
    """构建演示功能左侧的导航 tab 栏，每个 tab 对应一个独立的演示页面/文件。

    tab 的 href 统一指向 /examples/example/<name>，与 xnote_handlers/examples 模块路径一致，
    满足 xmanager 的 URL 前缀校验（模块路径 == URL 前缀）。
    """
    tab = TabBox(tab_key="name", title="案例:", css_class="btn-style", tab_default=tab_default)
    tab.add_tab("文本示例", value="text", href="/examples/example/text")
    tab.add_tab("按钮示例", value="btn", href="/examples/example/btn")
    tab.add_tab("Tab示例", value="tab", href="/examples/example/tab")
    tab.add_tab("Tag示例", value="tag", href="/examples/example/tag")
    tab.add_tab("Form示例", value="form", href="/examples/example/form")
    tab.add_tab("Dialog示例", value="dialog", href="/examples/example/dialog")
    tab.add_tab("Dropdown示例", value="dropdown", href="/examples/example/dropdown")
    tab.add_tab("Table示例", value="table", href="/examples/example/table")
    tab.add_tab("ListView示例", value="list", href="/examples/example/list")
    tab.add_tab("ListPlugin", value="list_plugin", href="/examples/example/list_plugin")
    tab.add_tab("Tree示例", value="tree", href="/examples/example/tree")
    tab.add_tab("日历组件", value="calendar", href="/examples/example/calendar")
    tab.add_tab("Hammer示例", value="hammer", href="/examples/example/hammer")
    return tab
