# encoding=utf-8
# Tab 示例 tab，对应 /examples/tab
from xutils import Storage
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xmanager
from xnote.plugin import TabBox, TabTable
from xnote_handlers.config import LinkConfig
from .example_nav import get_example_tab


class TabExampleHandler:

    def GET(self):
        user_name = xauth.current_name_str()
        xmanager.add_visit_log(user_name, "/examples/tab")

        kw = Storage()
        kw.title = "组件示例"
        kw.parent_link = LinkConfig.develop_index
        kw.example_tab = get_example_tab(tab_default="tab")

        title_width = "120px"
        tab_group_1 = TabBox(tab_key="tab_group_1", css_class="btn-style", title="Tab Group 1", title_width=title_width)
        tab_group_2 = TabBox(tab_key="tab_group_2", css_class="btn-style", title="Tab Group 2", title_width=title_width)

        for index in range(3):
            tab_group_1.add_item(title=f"Tab-{index}", value=f"tab-{index}")
            tab_group_2.add_item(title=f"Tab-{index}", value=f"tab-{index}")

        kw.tab_group_1 = tab_group_1
        kw.tab_group_2 = tab_group_2
        kw.tab_table = self.get_tab_table()

        return xtemplate.render("examples/page/example_tab.html", **kw)

    def POST(self):
        return self.GET()

    def get_tab_table(self):
        tab_table = TabTable()
        tab_group_1 = TabBox(tab_key="tab_group_1", css_class="btn-style", title="Tab Group 1")
        tab_group_2 = TabBox(tab_key="tab_group_2", css_class="btn-style", title="Tab Group 2")

        for index in range(3):
            tab_group_1.add_item(title=f"Tab-{index}", value=f"tab-{index}")
            tab_group_2.add_item(title=f"Tab-{index}", value=f"tab-{index}")

        tab_table.add_tab_box(tab_group_1)
        tab_table.add_tab_box(tab_group_2)
        return tab_table


xurls = (
    r"/examples/tab", TabExampleHandler,
)
