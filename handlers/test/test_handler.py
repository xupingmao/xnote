
import xutils
from xnote.core import xtemplate
from xnote.plugin.table_plugin import BaseTablePlugin

class handler:    
    def GET(self):
        return "success"
    
class TableExampleHandler(BaseTablePlugin):
    
    title = "表格测试"

    NAV_HTML = """
<div class="card">
    <button class="btn" onclick="xnote.table.handleEditForm(this)"
            data-url="?action=edit" data-title="新增记录">新增记录</button>
</div>
"""
    PAGE_HTML = NAV_HTML + BaseTablePlugin.TABLE_HTML

class ExampleHandler:

    def GET(self):
        name = xutils.get_argument("name", "")
        if name == "":
            return xtemplate.render("test/page/example_index.html")
        else:
            return xtemplate.render("test/page/example_%s.html" % name)

    def POST(self):
        return self.GET()

xurls = (
    r"/test", handler,
    r"/test/example", ExampleHandler,
    r"/test/example/table", TableExampleHandler,
)
