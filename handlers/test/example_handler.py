# encoding=utf-8
# Created by xupingmao on 2024/09/15
import xutils
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xmanager
from xnote.plugin.table_plugin import BaseTablePlugin


class TableExampleHandler(BaseTablePlugin):
    
    title = "表格测试"

    NAV_HTML = """
{% include test/component/example_nav_tab.html %}

<div class="card">
    <button class="btn" onclick="xnote.table.handleEditForm(this)"
            data-url="?action=edit" data-title="新增记录">新增记录</button>
</div>
"""
    PAGE_HTML = NAV_HTML + BaseTablePlugin.TABLE_HTML

class ExampleHandler:

    def GET(self):
        user_name = xauth.current_name_str()
        xmanager.add_visit_log(user_name, "/test/example")
        
        name = xutils.get_argument_str("name", "")
        if name == "":
            return xtemplate.render("test/page/example_index.html")
        else:
            return xtemplate.render(f"test/page/example_{name}.html")

    def POST(self):
        return self.GET()


xurls = (
    r"/test/example", ExampleHandler,
    r"/test/example/table", TableExampleHandler,
)