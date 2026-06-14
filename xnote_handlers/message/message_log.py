# encoding=utf-8

import xutils

from typing import Optional, List
from xutils import Storage
from xutils import webutil
from xutils import netutil
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core.xtemplate import T
from xnote.plugin import TabBox
from xnote_handlers.message import message_utils
from xnote_handlers.message import message_tag
from xnote_handlers.message.message_utils import format_filter_key
from .dao_template import MessageTemplateDao
from .message_template_service import handle_template_tab
from .message_utils import mark_filter_text
from .message_tab import get_message_log_tab
from xnote.core.xnote_user_config import UserConfig
from xutils.functions import uniq_list_add

class LogPageHandler:
            
    def do_get(self):
        key = xutils.get_argument_str("key", "")
        input_tag = xutils.get_argument_str("tag", "log")
        user_name = xauth.current_name_str()
        user_id = xauth.current_user_id()
        default_content = format_filter_key(key)
        filter_tag1 = xutils.get_argument_str("filter_tag1")
        filter_tag2 = xutils.get_argument_str("filter_tag2")
        filter_tag3 = xutils.get_argument_str("filter_tag3")
        
                
        filter_keys = []
        uniq_list_add(filter_keys, key)
        uniq_list_add(filter_keys, filter_tag1)
        uniq_list_add(filter_keys, filter_tag2)
        uniq_list_add(filter_keys, filter_tag3)
        
        filter_key = ",".join(filter_keys)

        kw = Storage()

        kw.tag=input_tag
        kw.message_tag=input_tag
        kw.search_type="message"
        kw.show_side_system_tags=True
        kw.html_title=T("随手记")
        kw.default_content=default_content
        kw.show_back_btn=False
        kw.message_tab="log"
        kw.message_placeholder="记录发生的事情/产生的想法"
        kw.side_tags=message_utils.list_hot_tags(user_name, 20)
        kw.search_ext_dict = dict(tag="log.search")
        kw.message_left_class = "hide"
        kw.message_right_class = "row"
        kw.message_tab_component = get_message_log_tab(user_name, input_tag)
        kw.filter_key = filter_key
        
        filter_content = UserConfig.msg_filter.get_str(user_id=user_id)
        kw.show_tag_filter = True
        kw.filter_config_key = UserConfig.msg_filter.key
        kw.filter_html = mark_filter_text(filter_content, link_type="log", selected_key=key)
        handle_template_tab(kw, default_content)
        
        return xtemplate.render("message/page/message_list_view.html", **kw)
    