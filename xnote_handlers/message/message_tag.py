# encoding=utf-8

import typing
import json
import xutils
import logging

from typing import List
from xnote.core import xauth, xtemplate, xconfig, xmanager
from xnote.core.xtemplate import T
from xutils import Storage, webutil, dateutil
from xutils.base import BaseDataRecord
from xutils.textutil import quote
from xutils.db.dbutil_helper import new_from_dict
from . import dao as msg_dao
from . import dao_filter
from . import message_utils
from .message_model import MsgTagInfo, MessageTagEnum
from .message_tab import get_message_log_tab, get_system_tag_tabs
from xutils.text_parser import TokenType
from xutils import netutil
from xutils.functions import safe_list
from xnote_handlers.note import dao_tag
from xnote_handlers.note.dao_tag import TagTypeEnum
from xnote.plugin.table_plugin import BaseTablePlugin


"""
随手记的标签处理
页面对应的是 ajax/message_tag_ajax.html 
"""
MAX_LIST_LIMIT = 1000


def get_tag_list():
    user_name = xauth.current_name_str()
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
        tag_info.custom_url = f"{server_home}/message/calendar?tag=log.date&date={date}&filterKey={quote(tag_name)}"
        tag_info.badge_info = f"{tag_info.amount}"
    result.sort(key = lambda x:x.amount, reverse=True)
    return result

def get_tag_list_by_month(user_id=0, month="2000-01", tag=""):
    date_start = month + "-01"
    date_end = dateutil.date_str_add(date_start, months=1)
    msg_list, amount = msg_dao.list_by_date_range(user_id=user_id, tag=tag, date_start=date_start, date_end=date_end)
    result = get_tag_list_by_msg_list(msg_list, date=month)
    return result

def filter_standard_msg_list(msg_list: typing.List[MsgTagInfo]):
    result = [] # type: list[MsgTagInfo]
    for item in msg_list:
        if message_utils.is_standard_tag(item.content):
            result.append(item)
    return result

def list_message_tags(user_name, offset=0, limit=20, *, orderby = "amount_desc", only_standard=False):
    msg_list = msg_dao.MsgTagInfoDao.list(user=user_name, offset=offset, limit=limit, order=orderby)

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
            if token.is_topic:
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

def update_tag_amount(tag_info: msg_dao.MsgTagInfo, user_id=0, key=""):
    amount = msg_dao.MsgTagBindDao.count_by_key(user_id=user_id, key=key)
    tag_info.amount = amount
    if amount == 0:
        msg_dao.MsgTagInfoDao.delete(tag_info)
    else:
        msg_dao.MsgTagInfoDao.update(tag_info)
    logging.info(f"user:{user_id},key:{key},amount:{amount}")


def update_tag_amount_by_msg(msg_item: msg_dao.MessageDO):
    """插入或者更新异步处理"""
    user_id = msg_item.user_id

    for keyword in safe_list(msg_item.keywords):
        # 只自动创建标准的tag
        if not message_utils.is_user_tag_or_heading(keyword):
            continue
        message = msg_dao.MsgTagInfoDao.get_or_create(msg_item.user_id, keyword)
        update_tag_amount(message, user_id, keyword)
    
    # 系统标签
    for keyword in safe_list(msg_item.system_tags):
        message = msg_dao.MsgTagInfoDao.get_or_create(msg_item.user_id, keyword)
        update_tag_amount(message, user_id, keyword)

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

def filter_tag_list(tag_list: typing.List[MsgTagInfo], only_standard=False):
    result : typing.List[MsgTagInfo] = []
    for item in tag_list:
        if only_standard and not message_utils.is_standard_tag(item.tag_code):
            continue
        result.append(item)
    return result

class ListTagAjaxHandler:

    @xauth.login_required()
    def GET(self):
        user_id = xauth.current_user_id()
        limit = xutils.get_argument_int("pagesize", 1000)
        tag_info_list = msg_dao.MsgTagInfoDao.list(user_id=user_id, offset=0, limit=limit)
        tag_info_list = filter_tag_list(tag_info_list, only_standard=True)
        return webutil.SuccessResult(tag_info_list)

class SearchDialogHandler:

    @xauth.login_required()
    def GET(self):
        user_id = xauth.current_user_id()
        limit = xutils.get_argument_int("pagesize", 1000)
        tag_info_list = msg_dao.MsgTagInfoDao.list(user_id=user_id, offset=0, limit=limit)
        tag_info_list = filter_tag_list(tag_info_list, only_standard=True)
        return xtemplate.render("message/page/message_tag_search_dialog.html", tag_list = tag_info_list)

class ListTagPage:
    
    @xauth.login_required()
    def GET(self):
        user_info = xauth.current_user()
        assert user_info != None
        user_name = user_info.name
        user_id = user_info.user_id
        xmanager.add_visit_log(user_name, "/message/tag/list")
        tag_category_list = dao_tag.list_tag_category_detail(user_id=user_id, tag_type=TagTypeEnum.msg_tag.int_value)
        
        kw = Storage()
        kw.html_title = T("随手记标签")
        kw.tag_category_list = tag_category_list
        kw.tab_default = "log.tags"
        kw.message_tab_component = get_message_log_tab(user_name, "log.tags")

        return xtemplate.render("message/page/message_tag.html", **kw)


class SystemTagHandler:
    
    @xauth.login_required()
    def GET(self):
        kw = self.create_kw()
        tag_code = xutils.get_argument_str("tag_code")
        user_name = xauth.current_name_str()
        kw.tag = "log"
        kw.tab_default = "log.tags"
        kw.message_tag= tag_code
        kw.search_type="message"
        kw.show_input_box=False
        kw.show_side_tags=False
        kw.message_left_class = "hide"
        kw.message_right_class = "row"
        kw.message_tab_component = get_message_log_tab(user_name, "log.tags")
        kw.system_tag_tabs = get_system_tag_tabs(tag_code)

        return xtemplate.render("message/page/message_list_view.html", **kw)
    

    def create_kw(self):
        return Storage()


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
        page_size = 20
        user_id = xauth.current_user_id()
        offset = webutil.get_page_offset(page, page_size)
        tag_list, total = msg_dao.MsgTagInfoDao.get_page(user_id=user_id, offset=offset, 
                                                         limit=page_size, order=orderby)
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
            page_max=webutil.get_page_max(total, page_size),
            item_list=tag_list
        )

        kw.page = page

        user_name = xauth.current_name_str()

        kw.top_keywords = []
        if orderby == "amount_desc" and page == 1:
            limit = self.get_recent_limit()
            kw.recent_keywords = get_recent_keywords(user_name, tag = "search", limit=limit)
            
        return xtemplate.render("message/page/message_tag_ajax.html", **kw)
    
    def get_recent_limit(self):
        if webutil.is_mobile_client():
            return 5
        return 20


class FilterEditHandler(BaseTablePlugin):
    """标签过滤器编辑器"""
    require_login = True
    require_admin = False
    
    def handle_edit(self):
        user_id = xauth.current_user_id()
        
        # 获取 filter_config_key 参数，决定是编辑 task_filter 还是 msg_filter
        filter_config_key = xutils.get_argument_str("filter_config_key", "task.filter")
        
        # 查询并解析过滤器配置
        filter_config = dao_filter.get_filter_config(user_id, filter_config_key)
        
        # 创建表单
        form = self.create_form()
        form.path = "/message/tag/filter"
        form.model_name = "filter"
        form.id = "filter_edit"
        
        # 添加隐藏字段存储 filter_config_key
        form.add_row("", "filter_config_key", css_class="hide", value=filter_config_key)
        
        # 添加待办过滤器字段
        form.add_textarea(
            title="tag1",
            field="tag1",
            placeholder="输入标签，使用空格、逗号或换行分隔",
            value=filter_config.get_tag1_str(),
            rows=5
        )
        
        # 添加随手记过滤器字段
        form.add_textarea(
            title="tag2",
            field="tag2",
            placeholder="输入标签，使用空格、逗号或换行分隔",
            value=filter_config.get_tag2_str(),
            rows=5
        )
        
        # 保留第三个字段以备将来扩展
        form.add_textarea(
            title="tag3",
            field="tag3",
            placeholder="输入标签，使用空格、逗号或换行分隔",
            value=filter_config.get_tag3_str(),
            rows=5
        )
        
        kw = Storage()
        kw.form = form
        return self.response_form(**kw)
    
    def handle_save(self):
        user_id = xauth.current_user_id()
        
        # 支持两种数据格式：
        # 1. 前端通过 JSON data 参数提交（BaseTablePlugin 标准方式）
        # 2. 直接通过表单字段提交（兼容测试）
        param_dict = self.get_data_dict()
        tag1 = param_dict.get_str("tag1", "")
        tag2 = param_dict.get_str("tag2", "")
        tag3 = param_dict.get_str("tag3", "")
        filter_config_key = param_dict.get_str("filter_config_key")
        if filter_config_key == "":
            return webutil.FailedResult(message="filter_config_key 不能为空")
    
        # 格式化标签：处理空格、逗号和换行
        tag1_list = message_utils.parse_tags_to_list(tag1)
        tag2_list = message_utils.parse_tags_to_list(tag2)
        tag3_list = message_utils.parse_tags_to_list(tag3)
        
        # 保存过滤器配置
        config_item = dao_filter.save_filter_config(
            user_id, tag1_list, tag2_list, tag3_list, filter_config_key)
        if config_item is None:
            return webutil.FailedResult(message="无效的过滤器配置")
        
        return webutil.SuccessResult(message="保存成功")
    
xurls = (
    r"/message/add_tag", AddTagHandler,
    r"/message/tag/delete", DeleteTagAjaxHandler,
    r"/message/tag/list", ListTagPage,
    r"/message/tag/list_ajax", ListAjaxHandler,
    r"/message/tag/search_dialog", SearchDialogHandler,
    r"/message/tag/system_tag", SystemTagHandler,
    r"/api/message/tag/list", ListTagAjaxHandler,
    r"/message/tag/filter", FilterEditHandler,
)
