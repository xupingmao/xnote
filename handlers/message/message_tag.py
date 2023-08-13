# encoding=utf-8

import xauth
import xutils
import xtemplate
from xutils import Storage, webutil
from . import dao as msg_dao

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

