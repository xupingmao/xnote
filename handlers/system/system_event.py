# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/05/18 09:44:13
# @modified 2022/03/12 11:07:34

from xnote.core import xmanager
from xnote.core.xtemplate import BasePlugin
from xnote.plugin.table_plugin import BaseTablePlugin
from xutils import Storage
from xnote.core import xtemplate
from xnote.plugin import sidebar, LinkConfig

class EventHandler(BaseTablePlugin):

    title = '系统事件'
    title_style = "left"
    category = "admin"
    parent_link = LinkConfig.app_index
    show_title = True
    show_aside = True
    require_admin = True
    show_pagenation = False
    NAV_HTML = """
<div class="card btn-line-height">
    <span>系统一共注册{{event_handler_count}}个事件处理器</span>
</div>
"""

    def get_aside_html(self):
        return sidebar.get_admin_sidebar_html()

    def handle_page(self):    
        self.show_aside = True
        event_type_list = []
        handlers = xmanager.get_event_manager()._handlers
        event_type_list = sorted(handlers.keys())
        
        count = 0
        for key in event_type_list:
            count += len(handlers[key])
        
        table = self.create_table()
        table.default_head_style.min_width = "100px"
        table.add_head("事件名称", field="name", min_width="150px")
        table.add_head("事件处理器", field="func_name", min_width="200px")
        table.add_head("描述", field="description")
        table.add_head("备注", field="remark")
        table.add_head("是否异步", field="is_async")

        for key in event_type_list:
            event_handlers = handlers[key]
            for handler in event_handlers:
                row = dict()
                row["name"] = key
                row["func_name"] = handler.func_name
                row["description"] = handler.description
                row["is_async"] = handler.is_async
                row["remark"] = handler.remark
                table.add_row(row)


        kw = Storage()
        kw.table = table
        kw.event_handler_count = count
        return self.response_page(**kw)
    
xurls = (
    r"/system/event", EventHandler
)