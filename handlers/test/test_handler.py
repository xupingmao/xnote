# encoding=utf-8

import xutils
import web
import time

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


class TestCacheHandler:

    def format_time(self, gmtime):
        return time.strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime)

    def GET(self):
        cache_type = xutils.get_argument_int("type")
        etag = xutils.get_argument_str("etag")
        if cache_type == 1:
            return self.get_cache_1()
        
        environ = web.ctx.environ
        client_etag = environ.get('HTTP_IF_NONE_MATCH')
        if_modified_since = environ.get("HTTP_IF_MODIFIED_SINCE")
        print(f"client_etag={client_etag}, if_modified_since={if_modified_since}")

        modified = time.gmtime()
        expires = time.gmtime(time.time() + 3600*24)

        web.header("Last-Modified", self.format_time(modified))
        web.header("Etag", etag)
        web.header("Expires", self.format_time(expires))
        return "test cache"
    
    def get_cache_1(self):
        expire_seconds = 3600 * 24
        web.header("Cache-Control", "public")
        web.header("Cache-Control", f"max-age={expire_seconds}")
        web.header("Vary", "User-Agent")
        return "test cache"


xurls = (
    r"/test", handler,
    r"/test/example", ExampleHandler,
    r"/test/example/table", TableExampleHandler,
    r"/test/cache", TestCacheHandler,
)
