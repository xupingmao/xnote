# encoding=utf-8

import xauth
import xutils
import xtemplate
from xutils import Storage, webutil
from . import dao as msg_dao
from . import message_utils

"""
随手记的标签处理
页面对应的是 ajax/message_tag_ajax.html 
"""
MAX_LIST_LIMIT = 1000

def get_tag_list():
    user_name = xauth.current_name()
    offset = 0
    msg_list, amount = msg_dao.list_by_tag(
        user_name, "key", offset, MAX_LIST_LIMIT)
    return webutil.SuccessResult(data=msg_list)


def get_log_tags_page():
    """随手记的话题标签页面"""
    orderby = xutils.get_argument("orderby", "")

    kw = Storage(
        tag="key",
        search_type="message",
        show_tag_btn=False,
        show_attachment_btn=False,
        show_system_tag=True,
        message_placeholder="添加标签/关键字/话题",
        show_side_tags=False,
    )

    kw.show_input_box = False
    kw.show_sub_link = False
    kw.orderby = orderby

    return xtemplate.render("message/page/message_list_view.html", **kw)


def filter_standard_msg_list(msg_list):
    result = []
    for item in msg_list:
        if message_utils.is_standard_tag(item.content):
            result.append(item)
    return result

def list_message_tags(user_name, offset, limit, *, orderby = "amount_desc", only_standard=False):
    msg_list, amount = msg_dao.list_by_tag(
        user_name, "key", 0, MAX_LIST_LIMIT)
    
    if only_standard:
        msg_list = filter_standard_msg_list(msg_list)

    p = message_utils.MessageKeyWordProcessor(msg_list)
    p.process()
    p.sort(orderby)

    return msg_list[offset:offset+limit], len(msg_list)

def get_recent_keywords(user_name: str, tag: str):
    """获取最近访问的标签"""
    msg_list, amount = list_message_tags(user_name, 0, 20, orderby = "recent", only_standard=True)
    parser = message_utils.MessageListParser(msg_list, tag=tag)
    parser.parse()
    result = parser.get_message_list()
    for item in result:
        item.badge_info = ""
    return result