# encoding=utf-8

import time
import xutils
from xnote.core import xmanager, xconfig, xauth, xtemplate

from . import dao, message_utils
from xutils import SearchResult, u, Storage, functions

@xmanager.searchable()
def on_search_message(ctx):
    if ctx.search_message is False:
        return

    key = ctx.key
    message_utils.touch_key_by_content(ctx.user_name, 'key', key)
    max_len = xconfig.SEARCH_SUMMARY_LEN

    messages, count = dao.search_message(ctx.user_name, key, 0, 3)
    search_result = []
    for message in messages:
        item = SearchResult()
        if message.content != None and len(message.content) > max_len:
            message.content = message.content[:max_len] + "......"
        message_utils.process_message(message)
        item.tag_name = u("记事")
        item.tag_class = "orange"
        item.name = u('记事 - ') + message.ctime
        item.html = message.html
        item.icon = "hide"
        search_result.append(item)
        # print(message)

    show_message_detail = xconfig.get_user_config(
        ctx.user_name, "search_message_detail_show")

    if show_message_detail == "false":
        search_result = []

    if count > 0:
        more = SearchResult()
        more.name = "搜索到[%s]条记事" % count
        more.url = "/message?key=" + ctx.key
        more.icon = "fa-file-text-o"
        more.show_more_link = True
        search_result.insert(0, more)

    if len(search_result) > 0:
        ctx.messages += search_result




class SearchContext:

    def __init__(self, key):
        self.key = key



class SearchHandler:
    """搜索逻辑处理"""

    def get_page(self):
        user_name = xauth.current_name()
        key = xutils.get_argument_str("key", "")
        tag = xutils.get_argument_str("tag", "search")

        kw = Storage()
        kw.tag = tag
        kw.key = key
        kw.keyword = key
        kw.default_content = message_utils.filter_key(key)
        kw.side_tags = message_utils.list_hot_tags(user_name, 20)
        kw.create_tag = self.get_create_tag()
        kw.show_create_on_tag = kw.create_tag != "forbidden"
        kw.is_keyword_marked = message_utils.is_marked_keyword(user_name, key)
        kw.is_task_tag = message_utils.is_task_tag(tag)
        kw.search_type = message_utils.TagHelper.get_search_type(tag)
        kw.search_ext_dict = dict(tag = tag)

        return xtemplate.render("message/page/message_search.html", **kw)

    def get_ajax_data(self, *, user_name="", key="", offset=0,
                      limit=20, search_tags=None, no_tag=False, date=""):
        start_time = time.time()
        chatlist, amount = dao.search_message(
            user_name, key, offset, limit,
            search_tags=search_tags, no_tag=no_tag, date=date)

        # 搜索扩展
        xmanager.fire("message.search", SearchContext(key))

        # 自动置顶
        message_utils.touch_key_by_content(user_name, "key", key)
        similar_key = message_utils.get_similar_key(key)
        if key != similar_key:
            message_utils.touch_key_by_content(user_name, "key", similar_key)

        cost_time = functions.second_to_ms(time.time() - start_time)

        dao.add_search_history(user_name, key, cost_time)

        return chatlist, amount

    def search_items(self, user_name, key):
        pass

    def get_create_tag(self):
        p = xutils.get_argument("p", "")
        if p == "task":
            return "task"

        if p == "log":
            return "log"

        return "forbidden"

