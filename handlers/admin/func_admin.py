# encoding=utf-8
"""函数管理"""
from xnote.core.xtemplate import BasePlugin
from xutils import Storage
from xutils import func_util
from xnote.core.template import DataTable
HTML = r"""
<style>
    .card-body {
        display:none;
    }
</style>

<div class="row">
    <div class="card btn-line-height">
        <span>系统一共注册{{len(functions)}}个函数</span>
    </div>
</div>

<div class="card">
    {% include common/table/table.html %}
</div>
"""

ASIDE_HTML = """
{% include system/component/admin_nav.html %}
"""


class FunctionsHandler(BasePlugin):
    
    title = '函数管理'
    
    def handle(self, content=""):
        self.rows = 0
        self.show_aside = True
        function_dict = func_util.get_func_dict()
        functions = []
        
        table = DataTable()
        table.add_head("名称", "name", width="30%")
        table.add_head("函数", "callable", width="70%")
        
        for name in function_dict:
            func = dict(name=name, callable=function_dict[name])
            functions.append(func)
        
        functions.sort(key = lambda x:x["name"])
        table.set_rows(functions)
        
        kw = Storage()
        kw.functions = functions
        kw.table = table
        
        self.writehtml(HTML, **kw)
        self.write_aside(ASIDE_HTML)
    
xurls = (
    r"/admin/functions", FunctionsHandler
)