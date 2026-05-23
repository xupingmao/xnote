# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/05/18 09:44:13
# @modified 2022/03/12 11:07:34

from xnote.core import xmanager
from xnote.core.xtemplate import BasePlugin
from xnote.plugin.table_plugin import BaseTablePlugin
from xutils import Storage
from xnote.core import xtemplate
from xnote.plugin import sidebar
from xnote_handlers.config import LinkConfig
from xnote.webui import ListView, ListViewItem, Card

class EventHandler(BaseTablePlugin):

    title = '事件注册'
    title_style = "left"
    category = "admin"
    parent_link = LinkConfig.app_index
    show_title = True
    show_aside = True
    require_admin = True
    show_pagenation = False
    NAV_HTML = """
<div class="card btn-line-height padding-x-mid">
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
        
        list_view = ListView()
        for key in event_type_list:
            event_handlers = handlers[key]
            for handler in event_handlers:
                item_text = f"{key}"
                list_item = ListViewItem()
                list_item.add_span(item_text, css_class="bold")
                list_item.add_br()
                list_item.add_span(f"处理器: {handler.func_name}")
                if handler.description:
                    list_item.add_span(f" | 描述: {handler.description}")
                if handler.remark:
                    list_item.add_span(f" | 备注: {handler.remark}")
                if handler.is_async:
                    list_item.add_span(f" | 异步执行")
                list_view.add(list_item)

        self.writehtml(self.NAV_HTML, event_handler_count=count)
        card = Card()
        card.add(list_view)
        self.add_component(card)
    
xurls = (
    r"/system/event", EventHandler
)