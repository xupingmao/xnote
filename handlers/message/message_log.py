# encoding=utf-8

import xutils


from xutils import Storage
from xutils import webutil
from xutils import netutil
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core.xtemplate import T
from handlers.message import message_utils
from handlers.message import message_tag
from handlers.message.message_utils import filter_key

class LogPageHandler:

    def do_get(self):
        key = xutils.get_argument_str("key", "")
        input_tag = xutils.get_argument_str("tag", "log")
        user_name = xauth.current_name_str()
        default_content = filter_key(key)

        kw = Storage()

        kw.tag=input_tag
        kw.message_tag=input_tag
        kw.search_type="message"
        kw.show_system_tag=False
        kw.show_side_system_tags=True
        kw.show_sub_link=False
        kw.html_title=T("随手记")
        kw.default_content=default_content
        kw.show_back_btn=False
        kw.message_tab="log"
        kw.message_placeholder="记录发生的事情/产生的想法"
        kw.side_tags=message_utils.list_hot_tags(user_name, 20)
        kw.search_ext_dict = dict(tag="log.search")
        kw.message_left_class = "hide"
        kw.message_right_class = "row"
        
        return xtemplate.render("message/page/message_list_view.html", **kw)
    