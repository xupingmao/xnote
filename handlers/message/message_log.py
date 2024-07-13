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
    
    def do_get_tags_ajax(self, msg_list, page=1, page_max=10):
        tag = xutils.get_argument_str("tag")
        display_tag = xutils.get_argument_str("displayTag")
        date = xutils.get_argument_str("date")
        key = xutils.get_argument_str("key")
        orderby = xutils.get_argument_str("orderby")
        filter_key = xutils.get_argument_str("filter_key")
        template_file = "message/ajax/message_tag_ajax.html"
        
        params = dict(
            tag=tag,
            displayTag=display_tag,
            key=key,
            date=date,
            filterKey=filter_key,
            orderby=orderby,
        )

        page_url = "?" + \
            netutil.build_query_string(
                params=params, skip_empty_value=True) + "&page="

        kw = Storage(
            page=page,
            page_url=page_url,
            page_max=page_max,
            item_list=msg_list
        )

        kw.page = page

        user_name = xauth.current_name_str()

        kw.top_keywords = []
        if orderby == "amount_desc" and page == 1:
            limit = self.get_recent_limit()
            kw.recent_keywords = message_tag.get_recent_keywords(user_name, tag = "search", limit=limit)
            
        return xtemplate.render(template_file, **kw)
    
    def get_recent_limit(self):
        if webutil.is_mobile_client():
            return 5
        return 20