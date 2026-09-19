# encoding=utf-8
# Dropdown 示例 tab，对应 /examples/dropdown
from xutils import Storage
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xmanager
from xnote_handlers.config import LinkConfig
from .example_nav import get_example_tab


class DropdownExampleHandler:

    def GET(self):
        user_name = xauth.current_name_str()
        xmanager.add_visit_log(user_name, "/examples/dropdown")

        kw = Storage()
        kw.title = "组件示例"
        kw.parent_link = LinkConfig.develop_index
        kw.example_tab = get_example_tab(tab_default="dropdown")
        return xtemplate.render("examples/page/example_dropdown.html", **kw)

    def POST(self):
        return self.GET()


xurls = (
    r"/examples/dropdown", DropdownExampleHandler,
)
