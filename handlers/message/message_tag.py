# encoding=utf-8

import typing
import xutils
from xnote.core import xauth, xtemplate, xconfig
from xutils import Storage, webutil, dateutil
from xutils.textutil import quote
from xutils.db.dbutil_helper import new_from_dict
from . import dao as msg_dao
from . import message_utils
from .message_model import MsgTagInfo, MessageTagEnum
from xutils.text_parser import TokenType
from xutils import netutil


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

def get_tag_list_by_msg_list(msg_list, date=""):
    p = message_utils.MessageListParser(msg_list)
    p.parse()
    result = p.get_keywords()
    server_home = xconfig.WebConfig.server_home
    for tag_info in result:
        tag_name = tag_info.name
        tag_info.url = f"{server_home}/message/calendar?tag=log.date&date={date}&filterKey={quote(tag_name)}"
        tag_info.badge_info = f"{tag_info.amount}"
    result.sort(key = lambda x:x.amount, reverse=True)
    return result

def get_tag_list_by_month(user_id=0, month="2000-01"):
    date_start = month + "-01"
    date_end = dateutil.date_str_add(date_start, months=1)
    msg_list, amount = msg_dao.list_by_date_range(user_id=user_id, date_start=date_start, date_end=date_end)
    result = get_tag_list_by_msg_list(msg_list, date=month)
    return result


def filter_standard_msg_list(msg_list: typing.List[MsgTagInfo]):
    result = [] # type: list[MsgTagInfo]
    for item in msg_list:
        if message_utils.is_standard_tag(item.content):
            result.append(item)
    return result

def list_message_tags(user_name, offset, limit, *, orderby = "amount_desc", only_standard=False):
    msg_list = msg_dao.MsgTagInfoDao.list(user=user_name, offset=0, limit=MAX_LIST_LIMIT)

    if only_standard:
        msg_list = filter_standard_msg_list(msg_list)

    p = message_utils.MessageKeyWordProcessor(msg_list)
    p.process()
    p.sort(orderby)

    return msg_list[offset:offset+limit], len(msg_list)

def get_recent_keywords(user_name: str, tag="search", limit =20):
    """获取最近访问的标签"""
    msg_list, amount = list_message_tags(user_name, 0, limit, orderby = "recent", only_standard=True)
    parser = message_utils.MessageListParser(msg_list, tag=tag)
    parser.parse()
    result = parser.get_message_list()
    for item in result:
        item.badge_info = ""
    return result

def add_tag_to_content(content="", new_tag=""):
    msg_struct = message_utils.mark_text_to_tokens(content=content)

    tags = []
    rest_str_list = []
    is_rest = False

    for token in msg_struct.tokens:
        if is_rest:
            rest_str_list.append(token.value)
        else:
            trim_value = token.value.strip()
            if token.is_topic():
                tags.append(token.value)
                continue
            
            if trim_value == "":
                continue

            # 既不是标签也不是空格
            is_rest = True
            rest_str_list.append(token.value)

    if new_tag not in tags:
        tags.append(new_tag)

    rest_text = "".join(rest_str_list).strip()
    return " ".join(tags) + "\n" + rest_text

class DeleteTagAjaxHandler:

    @xauth.login_required()
    def POST(self):
        tag_id = xutils.get_argument_int("tag_id")
        if tag_id == 0:
            return webutil.FailedResult("invalid tag_id")
        user_id = xauth.current_user_id()
        tag_info = msg_dao.MsgTagInfoDao.get_by_id(user_id=user_id, tag_id=tag_id)
        if tag_info is None:
            return webutil.FailedResult("标签不存在")
        msg_dao.MsgTagInfoDao.delete_by_id(tag_id=tag_id)
        return webutil.SuccessResult()


class AddTagHandler:

    @xauth.login_required()
    def POST(self):
        content = xutils.get_argument_str("content")
        new_tag = xutils.get_argument_str("new_tag")
        result = add_tag_to_content(content=content, new_tag=new_tag)
        return webutil.SuccessResult(result)

    def GET(self):
        return self.POST()

class ListTagAjaxHandler:

    @xauth.login_required()
    def GET(self):
        user_id = xauth.current_user_id()
        limit = xutils.get_argument_int("pagesize", 1000)
        tag_info_list = msg_dao.MsgTagInfoDao.list(user_id=user_id, offset=0, limit=limit)
        return webutil.SuccessResult(tag_info_list)

class ListTagPage:
    
    @xauth.login_required()
    def GET(self):
        sys_tag = xutils.get_argument_str("sys_tag")
        if MessageTagEnum.is_system_tag_code(sys_tag):
            return self.get_system_tag_page(sys_tag)
        return self.get_log_tags_page()
    
    def create_kw(self):
        kw = Storage()
        return kw

    def get_system_tag_page(self, tag):
        kw = self.create_kw()
        kw.message_tag=tag
        kw.search_type="message"
        kw.show_input_box=False
        kw.show_side_tags=False
        kw.message_left_class = "hide"
        kw.message_right_class = "row"

        return xtemplate.render("message/page/message_list_view.html", **kw)
    
    def get_log_tags_page(self):
        """随手记的话题标签页面"""
        orderby = xutils.get_argument_str("orderby", "")
        kw = self.create_kw()
        kw.list_ajax_url = "/message/tag/list_ajax"
        kw.tag="key"
        kw.search_type="message",
        kw.show_tag_btn=False
        kw.show_attachment_btn=False
        kw.show_system_tag=True
        kw.message_placeholder="添加标签/关键字/话题"
        kw.show_side_tags=False
        kw.show_input_box = False
        kw.show_sub_link = False
        kw.orderby = orderby
        kw.search_ext_dict = dict(tag="search")
        kw.show_left_tags = False
        kw.message_left_class = "hide"
        kw.message_right_class = "row"

        return xtemplate.render("message/page/message_list_view.html", **kw)


class ListAjaxHandler:

    @xauth.login_required()
    def GET(self):
        page = xutils.get_argument_int("page", 1)
        tag = xutils.get_argument_str("tag")
        display_tag = xutils.get_argument_str("displayTag")
        date = xutils.get_argument_str("date")
        key = xutils.get_argument_str("key")
        orderby = xutils.get_argument_str("orderby", "amount_desc")
        filter_key = xutils.get_argument_str("filter_key")
        template_file = "message/page/message_tag_ajax.html"
        page_size = 20
        user_id = xauth.current_user_id()
        offset = webutil.get_offset_by_page(page, page_size)
        tag_list, total = msg_dao.MsgTagInfoDao.get_page(user_id=user_id, offset=offset, limit=page_size)
        message_utils.format_tag_list(tag_list)
        message_utils.sort_tag_list(tag_list, orderby=orderby)

        params = dict(
            tag=tag,
            displayTag=display_tag,
            key=key,
            date=date,
            filterKey=filter_key,
            orderby=orderby,
        )

        query_string = netutil.build_query_string(params=params, skip_empty_value=True)
        page_url = f"?{query_string}&page="

        kw = Storage(
            page=page,
            page_url=page_url,
            page_max=webutil.get_page_max_by_total(total, page_size),
            item_list=tag_list
        )

        kw.page = page

        user_name = xauth.current_name_str()

        kw.top_keywords = []
        if orderby == "amount_desc" and page == 1:
            limit = self.get_recent_limit()
            kw.recent_keywords = get_recent_keywords(user_name, tag = "search", limit=limit)
            
        return xtemplate.render(template_file, **kw)
    
    def get_recent_limit(self):
        if webutil.is_mobile_client():
            return 5
        return 20

xurls = (
    r"/message/add_tag", AddTagHandler,
    r"/message/tag/delete", DeleteTagAjaxHandler,
    r"/message/tag/list", ListTagPage,
    r"/message/tag/list_ajax", ListAjaxHandler,
    r"/api/message/tag/list", ListTagAjaxHandler,
)
