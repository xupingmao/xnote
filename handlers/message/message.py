# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2017-05-29 00:00:00
@LastEditors  : xupingmao
@LastEditTime : 2024-03-07 23:35:01
@FilePath     : /xnote/handlers/message/message.py
@Description  : 描述
"""

"""短消息处理，比如任务、备忘、临时文件等等
tag: 短消息的类型
key/keyword: 短消息关键字
"""
import time
import math
import xutils
from xnote.core import xauth, xconfig, xmanager, xtemplate
import logging
from xutils import BaseRule, Storage, functions, u, SearchResult
from xutils import dateutil
from xnote.core.xtemplate import T
from xutils import netutil, webutil
from xutils.functions import safe_list
from xutils.textutil import quote
from handlers.message.message_task import TaskListHandler
from handlers.message.message_utils import (
    process_message,
    filter_key,
    filter_msg_list_by_key,
    format_message_stat,
    MessageListParser,
    get_remote_ip,
    get_length,
    get_tags_from_message_list,
    do_split_date,
    success,
    failure,
    convert_message_list_to_day_folder,
    count_month_size,
    touch_key_by_content,
    TagHelper,
)

from .message_utils import sort_keywords_by_marked
from . import dao, message_tag, message_search
from .dao import MessageDao
from handlers.message import message_utils
import handlers.message.dao as msg_dao

MSG_DAO = xutils.DAO("message")
# 消息处理规则
MSG_RULES = []
# 默认的标签
DEFAULT_TAG = "log"
MAX_LIST_LIMIT = 1000
# 系统标签
SYSTEM_TAG_TUPLE = ("book", "people", "file", "phone", "link")

LIST_VIEW_TPL = "message/page/message_list_view.html"

def get_current_message_stat():
    user_name = xauth.current_name()
    message_stat = MessageDao.get_message_stat(user_name)
    return format_message_stat(message_stat)


def update_keyword_amount(tag_info: msg_dao.MsgTagInfo, user_name="", key=""):
    user_id = xauth.UserDao.get_id_by_name(user_name)
    amount = dao.MsgTagBindDao.count_by_key(user_id=user_id, key=key)
    tag_info.amount = amount
    if amount == 0:
        msg_dao.MsgTagInfoDao.delete(tag_info)
    else:
        msg_dao.MsgTagInfoDao.update(tag_info)
    logging.info("user:%s,key:%s,amount:%s", user_name, key, amount)


@xutils.timeit(name="message.refresh", logfile=True)
def refresh_key_amount():
    pass


def refresh_message_index():
    """刷新随手记的索引"""
    pass


def get_page_max(amount, pagesize=None):
    if pagesize is None:
        pagesize = xconfig.PAGE_SIZE
    return math.ceil(amount / pagesize)


def get_offset_from_page(page, pagesize=None):
    if pagesize is None:
        pagesize = xconfig.PAGE_SIZE

    offset = (page - 1) * pagesize
    return max(offset, 0)


def after_message_create_or_update(msg_item):
    assert isinstance(msg_item, dao.MessageDO)
    process_message(msg_item)

    if get_length(msg_item.full_keywords) == 0:
        msg_item.no_tag = True
        msg_item.keywords = None
        MessageDao.update(msg_item)
    else:
        MessageDao.update_user_tags(msg_item)

    after_upsert(msg_item)

def after_message_delete(msg_item):
    process_message(msg_item)
    after_upsert(msg_item)

def after_upsert(msg_item):
    """插入或者更新异步处理"""
    user_name = msg_item.user

    for keyword in safe_list(msg_item.keywords):
        # 只自动创建标准的tag
        if not message_utils.is_standard_tag(keyword):
            continue
        message = get_or_create_keyword(user_name, keyword, msg_item.ip)
        update_keyword_amount(message, user_name, keyword)

class ListAjaxHandler:

    @xauth.login_required()
    def GET(self):
        pagesize = xutils.get_argument_int("pagesize", xconfig.PAGE_SIZE)
        page = xutils.get_argument_int("page", 1)
        tag = xutils.get_argument_str("tag", "task")
        format = xutils.get_argument_str("format")
        offset = get_offset_from_page(page, pagesize)

        assert isinstance(tag, str)

        user_name = xauth.get_current_name()

        chatlist, amount = self.do_list_message(
            user_name, tag, offset, pagesize)

        page_max = get_page_max(amount, pagesize)

        parser = MessageListParser(chatlist, tag=tag)
        parser.parse()
        chatlist = parser.get_message_list()

        if format == "html":
            return self.do_get_html(chatlist, page, page_max, tag)

        return dict(code="success", message="",
                    data=chatlist,
                    keywords=parser.get_keywords(),
                    amount=amount,
                    page_max=page_max,
                    pagesize=pagesize,
                    current_user=xauth.current_name())

    def do_list_message(self, user_name, tag, offset, pagesize):
        key = xutils.get_argument_str("key", "")
        date = xutils.get_argument_str("date", "")
        filter_date = xutils.get_argument_str("filterDate", "")

        if tag == "task.search":
            return self.do_search(user_name, key, offset, pagesize,search_tags=["task"])
        
        if tag == "done.search":
            return self.do_search(user_name, key, offset, pagesize, search_tags=["done"])

        if (tag in ("search", "log.search")) or (key != "" and key != None):
            # 搜索
            return self.do_search(user_name, key, offset, pagesize, search_tags=["log"])

        if tag in ("date", "log.date"):
            # 日期
            return self.do_list_by_date(user_name, date, offset, pagesize)

        if filter_date != "":
            return self.do_list_by_date(user_name, filter_date, offset, pagesize)

        if tag == "task":
            return self.do_list_task(user_name, offset, pagesize)

        if tag == "key":
            orderby = xutils.get_argument_str("orderby", "amount_desc")
            return message_tag.list_message_tags(user_name, offset, pagesize, orderby = orderby, only_standard=True)

        list_func = xutils.lookup_func("message.list_%s" % tag)
        if list_func != None:
            return list_func(user_name, offset, pagesize)
        else:
            return msg_dao.list_by_tag(user_name, tag, offset, pagesize)

    def do_get_html(self, msg_list, page: int, page_max: int, tag="task"):
        show_todo_check = True
        show_edit_btn = True
        show_to_log_btn = False
        display_tag = xutils.get_argument("displayTag", "")
        date = xutils.get_argument("date", "")
        key = xutils.get_argument("key", "")
        filter_key = xutils.get_argument("filterKey", "")
        orderby = xutils.get_argument("orderby", "")
        p = xutils.get_argument("p", "")
        xutils.get_argument_bool("show_marked_tag", True)

        show_edit_btn = (p != "done")

        if tag == "todo" or tag == "task":
            show_todo_check = True
            show_to_log_btn = True

        if tag == "done":
            show_to_log_btn = True

        if tag == "key":
            show_edit_btn = False

        if tag == "key":
            template_file = "message/ajax/message_tag_ajax.html"
        else:
            template_file = "message/ajax/message_ajax.html"

        params = dict(
            tag=tag,
            displayTag=display_tag,
            key=key,
            date=date,
            filterKey=filter_key,
            orderby=orderby,
            p=p,
        )

        page_url = "?" + \
            netutil.build_query_string(
                params=params, skip_empty_value=True) + "&page="

        kw = Storage(
            show_todo_check=show_todo_check,
            show_edit_btn=show_edit_btn,
            show_to_log_btn=show_to_log_btn,
            page=page,
            page_url=page_url,
            page_max=page_max,
            item_list=msg_list
        )

        if tag == "key":
            user_name = xauth.current_name()
            assert isinstance(user_name, str)
            kw.top_keywords = []
            if orderby == "amount_desc" and page == 1:
                kw.recent_keywords = message_tag.get_recent_keywords(user_name, tag = tag)
                
        return xtemplate.render(template_file, **kw)
    
    def get_top_keywords(self, msg_list):
        """返回热门的标签"""
        result = []
        for item in msg_list:
            if item.is_marked:
                result.append(item)
        return result

    def do_search(self, user_name, key, offset, pagesize, search_tags=None):
        # 搜索
        no_tag = False

        input_search_tags = xutils.get_argument_str("searchTags")
        input_no_tag = xutils.get_argument("noTag", "false")
        p = xutils.get_argument("p", "")
        date = xutils.get_argument_str("date")

        if search_tags == None:
            if input_search_tags != "":
                search_tags = input_search_tags.split(",")
            if p == "task":
                search_tags = ["task"]
            if p == "done":
                search_tags = ["done"]
            if p == "log":
                search_tags = ["log"]

        if input_no_tag == "true":
            no_tag = True

        searcher = message_search.SearchHandler()
        return searcher.get_ajax_data(user_name=user_name, key=key, offset=offset,
                                      limit=pagesize, search_tags=search_tags,
                                      no_tag=no_tag, date=date)

    def do_list_task(self, user_name, offset, limit):
        p = xutils.get_argument("p", "")
        filter_key = xutils.get_argument("filterKey", "")
        status = xutils.get_argument("status", "")

        if p == "done":
            return msg_dao.list_task_done(user_name, offset, limit)

        if filter_key != "":
            msg_list, amount = msg_dao.list_task(
                user_name, offset=0, limit=MAX_LIST_LIMIT)
            msg_list = filter_msg_list_by_key(msg_list, filter_key)
            return msg_list[offset:offset+limit], len(msg_list)
        else:
            return msg_dao.list_task(user_name, offset, limit)

    def do_list_by_date(self, user_name, date, offset, pagesize):
        filter_key = xutils.get_argument_str("filterKey", "")

        if filter_key != "":
            msg_list, amount = msg_dao.list_by_date(
                user_name, date, 0, MAX_LIST_LIMIT)
            msg_list = filter_msg_list_by_key(msg_list, filter_key)
            return msg_list[offset:offset+pagesize], len(msg_list)
        else:
            return msg_dao.list_by_date(user_name, date, offset, pagesize)


def update_message_status(id, status):
    user_name = xauth.current_name()
    data = MessageDao.get_by_id(id)
    if data and data.user == user_name:
        data.status = status
        data.mtime = xutils.format_datetime()

        MessageDao.update(data)
        MessageDao.refresh_message_stat(user_name, ["task", "done"])

        event = Storage(id=id, user=user_name,
                        status=status, content=data.content)
        xmanager.fire("message.updated", event)
        xmanager.fire("message.update", event)
        return dict(code="success")
    else:
        return failure(message="无操作权限")


def update_message_content(id, user_name, content):
    data = MessageDao.get_by_id(id)
    if data and data.user == user_name:
        if data.user_id == 0:
            data.user_id = xauth.UserDao.get_id_by_name(user_name)
            
        # 先保存历史
        MessageDao.add_history(data)
        
        data.content = content
        data.mtime = xutils.format_datetime()
        data.version = data.get('version', 0) + 1
        MessageDao.update(data)

        xmanager.fire("message.update", dict(
            id=id, user=user_name, content=content))

        after_message_create_or_update(data)


def create_done_message(old_message):
    old_id = old_message['id']

    new_message = dao.MessageDO()
    new_message.ref = old_id
    new_message.tag = 'done'
    new_message.user = old_message['user']
    new_message.ctime = xutils.format_datetime()
    MessageDao.create(new_message)


def update_message_tag(id, tag):
    """更新message的tag字段"""
    user_name = xauth.current_name()
    data = MessageDao.get_by_id(id)
    if data == None:
        return webutil.FailedResult(message="数据不存在")
    if data.user != user_name:
        return webutil.FailedResult(message="无权操作")
    
    # 修复status数据，全部采用tag
    data.pop("status", None)
    data.tag = tag
    data.mtime = xutils.format_datetime()
    data.sort_value = data.mtime
    need_update = True
    
    if tag == "done":
        # 任务完成时除了标记原来任务的完成时间，还要新建一条消息
        data.done_time = xutils.format_datetime()
        data.mtime = xutils.format_datetime()
        data.append_comment("$mark_task_done$")
    
    if tag == "task":
        # 重新开启任务
        data.append_comment("$reopen_task$")

        ref = data.ref
        origin_data = MessageDao.get_by_id(ref)
        if origin_data != None:
            # 更新原始任务后删除当前的完成记录
            origin_data.append_comment("$reopen_task$")
            MessageDao.update_tag(origin_data, tag, sort_value = origin_data.sort_value)
            MessageDao.delete_by_key(data.id)
            need_update = False
    
    if need_update:    
        MessageDao.update_tag(data, tag, sort_value=data.sort_value)

    xmanager.fire("message.updated", Storage(
        id=id, user=user_name, tag=tag, content=data.content))

    return webutil.SuccessResult()


class FinishMessageAjaxHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("id")
        if id == "":
            return
        return update_message_tag(id, "done")


class OpenMessageAjaxHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("id")
        if id == "":
            return
        return update_message_tag(id, "task")


class UpdateTagAjaxHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument_str("id")
        tag = xutils.get_argument_str("tag")
        if id == "":
            return webutil.FailedResult(code="404", message="id为空")

        if tag in ("task", "cron", "log", "key", "done"):
            return update_message_tag(id, tag)
        else:
            return webutil.FailedResult(message="无效的标签: %s" % tag)

class TouchAjaxHandler:

    def do_touch_by_id(self, id):
        msg = MessageDao.get_by_id(id)
        if msg is None:
            return failure(message="message not found, id:%s" % id)
        if msg.user != xauth.current_name():
            return failure(message="not authorized")
        msg.mtime = xutils.format_datetime()
        MessageDao.update(msg)
        return success()

    def do_touch_by_key(self, key):
        user_name = xauth.current_name()
        touch_key_by_content(user_name, "key", key)
        return success()

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("id")
        key = xutils.get_argument("key")

        if id != None and id != "":
            return self.do_touch_by_id(id)
        elif key != "":
            return self.do_touch_by_key(key)
        else:
            return failure(message="id or key is missing")


class DeleteAjaxHandler:

    def delete_msg(self, msg: msg_dao.MessageDO):
        if msg.user != xauth.current_name():
            return dict(code="fail", message="no permission")

        # 先保存历史
        MessageDao.add_history(msg)

        # 删除并刷新统计信息
        MessageDao.delete_by_key(msg.id)
        if msg.tag == "done" and msg.ref != None:
            MessageDao.delete_by_key(msg.ref)
            
        MessageDao.refresh_message_stat(msg.user, [msg.tag])
        after_message_delete(msg)

        return webutil.SuccessResult()
    
    def delete_tag(self, tag_info: msg_dao.MsgTagInfo):
        if tag_info.user != xauth.current_name_str():
            return webutil.FailedResult(message="no permission")
        
        msg_dao.MsgTagInfoDao.delete(tag_info)
        return webutil.SuccessResult()

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument_str("id")
        if id == "":
            return failure(message="id为空")

        try:
            msg = MessageDao.get_by_id(id)
            if msg != None:
                return self.delete_msg(msg)
            tag_info = msg_dao.MsgTagInfoDao.get_by_key(id)
            if tag_info != None:
                return self.delete_tag(tag_info)
            return webutil.FailedResult(message="数据不存在")
        except:
            xutils.print_exc()
            return webutil.FailedResult(message="删除失败")


class CalendarRule(BaseRule):

    def execute(self, ctx, date, month, day):
        print(date, month, day)
        ctx.type = "calendar"


def create_message(user_name, tag, content, ip):
    assert isinstance(user_name, str)
    assert isinstance(tag, str)
    assert isinstance(content, str)

    date = xutils.get_argument_str("date", xutils.format_date())
    content = content.strip()
    ctime = xutils.format_datetime()

    message = dao.MessageDO()
    message.user = user_name
    message.user_id = xauth.UserDao.get_id_by_name(user_name)
    message.tag = tag
    message.ip = ip
    message.date = date
    message.ctime = ctime
    message.mtime = ctime
    message.content = content
    message.sort_value = ctime
    
    id = MessageDao.create(message)
    MessageDao.refresh_message_stat(user_name, [message.tag])

    created_msg = MessageDao.get_by_id(id)
    assert created_msg != None
    
    after_message_create_or_update(created_msg)

    create_event = dict(id=id, user=user_name, content=content, ctime=ctime)
    xmanager.fire('message.add', create_event)
    xmanager.fire('message.create', create_event)

    return message

def get_or_create_keyword(user_name, content="", ip=""):
    return msg_dao.MsgTagInfoDao.get_or_create(user_name, content)

class SaveAjaxHandler:

    def apply_rules(self, user_name, id, tag, content):
        global MSG_RULES
        ctx = Storage(id=id, content=content, user=user_name, type="")
        for rule in MSG_RULES:
            rule.match_execute(ctx, content)

    @xauth.login_required()
    def do_post(self):
        id = xutils.get_argument("id")
        content = xutils.get_argument_str("content")
        tag = xutils.get_argument_str("tag", DEFAULT_TAG)
        location = xutils.get_argument_str("location", "")
        user_name = xauth.get_current_name()
        ip = get_remote_ip()

        if content == "":
            return dict(code="fail", message="输入内容为空!")
        
        tag = TagHelper.get_create_tag(tag)

        # 对消息进行语义分析处理，后期优化把所有规则统一管理起来
        self.apply_rules(user_name, id, tag, content)

        if id == "" or id is None:
            message = create_message(user_name, tag, content, ip)
            return webutil.SuccessResult(data=message)
        else:
            update_message_content(id, user_name, content)
        return webutil.SuccessResult(data=dict(id=id))

    def POST(self):
        try:
            return self.do_post()
        except Exception as e:
            xutils.print_exc()
            return webutil.FailedResult(code="fail", message=str(e))


class DateAjaxHandler:

    @xauth.login_required()
    def GET(self):
        date = xutils.get_argument_str("date", "")
        page = xutils.get_argument("page", 1, type=int)
        filter_key = xutils.get_argument_str("filterKey")
        user_id = xauth.current_user_id()

        if date == "":
            return xtemplate.render("error.html", error="date参数为空")

        offset = get_offset_from_page(page)
        limit = xconfig.PAGE_SIZE

        msg_list, msg_count = message_utils.list_by_date_and_key(
            user_id=user_id, month=date, offset=offset, limit=limit, filter_key=filter_key)

        parser = MessageListParser(msg_list)
        parser.parse()

        page_max = get_page_max(msg_count, xconfig.PAGE_SIZE)

        return xtemplate.render("message/ajax/message_ajax.html",
                                page_max=page_max,
                                page=page,
                                page_url=f"?date={date}&filterKey={quote(filter_key)}&page=",
                                item_list=msg_list)

class MessageListHandler:

    @xauth.login_required()
    def do_get(self, tag="task"):
        """随手记/待办的入口
        xxx_page 返回页面
        xxx_data 返回数据
        """
        user = xauth.current_name()
        key = xutils.get_argument("key", "")
        from_ = xutils.get_argument("from", "")
        type_ = xutils.get_argument("type", "")
        show_tab = xutils.get_argument_bool("show_tab", True)
        op = xutils.get_argument("op", "")
        date = xutils.get_argument("date", "")
        p = xutils.get_argument("p", "")

        # 记录日志
        assert isinstance(user, str)
        xmanager.add_visit_log(user, "/message?tag=%s" % tag)

        if tag == "month_tags":
            return self.do_view_month_tags()

        if tag in ("date", "log.date"):
            return self.do_view_by_date(date)

        if tag == "key" and op == "select":
            return self.do_select_key()

        if tag == "api.tag_list":
            return self.get_tag_list()

        if tag == "key":
            return self.get_log_tags_page()

        if tag == "task":
            return self.get_task_page()

        if tag == "task.tags":
            return TaskListHandler.get_task_taglist_page()

        if tag in ("search", "task.search", "done.search") or type_ == "search":
            return message_search.SearchHandler().get_page()

        if tag == "log.tags":
            return self.get_log_tags_page()
        
        return self.get_log_page()

    def do_select_key(self):
        user_name = xauth.current_name()
        offset = 0
        msg_list, amount = dao.list_by_tag(
            user_name, "key", offset, MAX_LIST_LIMIT)

        return xtemplate.render("message/page/message_tag_select.html",
                                msg_list=msg_list,
                                show_nav=False)
    
    def get_tag_list(self):
        return message_tag.get_tag_list()

    def get_log_tags_page(self):
        sys_tag = xutils.get_argument_str("sys_tag")
        if sys_tag in SYSTEM_TAG_TUPLE:
            return self.get_system_tag_page(sys_tag)

        return message_tag.get_log_tags_page()

    def get_system_tag_page(self, tag):
        kw = Storage(
            message_tag=tag,
            search_type="message",
            show_input_box=False,
            show_side_tags=False,
        )

        return xtemplate.render("message/page/message_list_view.html", **kw)

    def get_task_kw(self):
        return TaskListHandler.get_task_kw()

    def get_task_page(self):
        filter_key = xutils.get_argument_str("filterKey", "")
        page_name = xutils.get_argument_str("p", "")

        if page_name == "create":
            return TaskListHandler.get_task_create_page()

        if page_name == "done":
            return TaskListHandler.get_task_done_page()

        if page_name == "taglist":
            return TaskListHandler.get_task_taglist_page()

        if filter_key != "":
            return TaskListHandler.get_task_by_keyword_page(filter_key)
        else:
            # 任务的首页
            return TaskListHandler.get_task_create_page()

    def get_task_home_page(self):
        return TaskListHandler.get_task_create_page()

    def do_view_month_tags(self):
        user_name = xauth.current_name()
        date = xutils.get_argument_str("date")

        year, month, mday = do_split_date(date)

        msg_list, amount = msg_dao.list_by_date(
            user_name, date, limit=MAX_LIST_LIMIT)

        tag_list = get_tags_from_message_list(msg_list, "date", date)

        return xtemplate.render("message/page/message_tag_view.html",
                                year=year,
                                month=month,
                                message_tag="calendar",
                                search_type="message",
                                show_back_btn=True,
                                tag_list=tag_list,
                                html_title=T("待办任务"),
                                message_placeholder="添加待办任务")

    def get_log_page(self):
        key = xutils.get_argument("key", "")
        input_tag = xutils.get_argument("tag", "log")
        p = xutils.get_argument("p", "")
        user_name = xauth.current_name()
        default_content = filter_key(key)

        kw = Storage(
            tag=input_tag,
            message_tag=input_tag,
            search_type="message",
            show_system_tag=False,
            show_side_system_tags=True,
            show_sub_link=False,
            html_title=T("随手记"),
            default_content=default_content,
            show_back_btn=False,
            message_tab="log",
            message_placeholder="记录发生的事情/产生的想法",
            side_tags=message_utils.list_hot_tags(user_name, 20),
        )

        kw.search_ext_dict = dict(tag="log.search")

        return xtemplate.render("message/page/message_list_view.html", **kw)

    def do_view_by_date(self, date):
        kw = Storage()
        kw.message_placeholder = "补充%s发生的事情" % date

        filter_key = xutils.get_argument("filterKey", "")
        if filter_key != "":
            kw.show_input_box = False

        return xtemplate.render("message/page/message_list_view.html",
                                tag="date",
                                message_tag="date",
                                search_type="message",
                                show_system_tag=False,
                                show_sub_link=False,
                                html_title=T("随手记"),
                                show_back_btn=True,
                                **kw)

    def GET(self):
        tag = xutils.get_argument_str("tag")
        return self.do_get(tag)

class MessageDetailAjaxHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument_str("id")
        user_name = xauth.current_name_str()
        detail = msg_dao.get_message_by_id(id, user_name=user_name)
        if detail == None:
            return webutil.FailedResult(message="数据不存在")

        if detail.ref != None:
            detail = msg_dao.get_message_by_id(detail.ref, user_name=user_name)
        
        return dict(code="success", data = detail)

class CalendarHandler:

    @xauth.login_required()
    def GET(self):
        user_id = xauth.current_user_id()
        date = xutils.get_argument("date")

        year, month, mday = do_split_date(date)

        date = "%s-%02d" % (year, month)

        kw = Storage()
        kw.tag = "log.date"
        kw.year = year
        kw.month = month
        kw.date = date
        kw.html_title = T("随手记")
        kw.search_type = "message"
        kw.tag_list = message_tag.get_tag_list_by_month(user_id=user_id, month=date)

        return xtemplate.render("message/page/message_calendar.html", **kw)


class StatAjaxHandler:

    @xauth.login_required()
    def GET(self):
        user = xauth.current_name_str()
        stat = msg_dao.get_message_stat(user)
        format_message_stat(stat)
        return stat


class MessageHandler(MessageListHandler):
    pass


class MessageLogHandler(MessageHandler):

    def GET(self):
        return self.do_get("log")


class TodoHandler(MessageHandler):

    @xauth.login_required()
    def do_get(self, tag="todo", title="待办任务", show_input_box=True):
        user_name = xauth.current_name()
        assert isinstance(user_name, str)
        message_stat = msg_dao.get_message_stat(user_name)
        xmanager.add_visit_log(user_name, "/message/todo")

        return xtemplate.render("message/page/message_todo.html",
                                search_type="task",
                                tag=tag,
                                title=T(title),
                                show_input_box=show_input_box,
                                message_stat=message_stat)

    def GET(self):
        return self.do_get("todo")


class TodoDoneHandler(TodoHandler):

    def GET(self):
        return self.do_get("done", "已完成任务", show_input_box=False)


class TodoCanceledHandler(TodoHandler):

    def GET(self):
        return self.do_get("canceled", "已取消任务", show_input_box=False)


def get_default_year_and_month():
    return dateutil.format_date(None, "%Y-%m")


class MessageListByDayHandler():

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
        date = xutils.get_argument("date", "")
        show_empty = xutils.get_argument("show_empty", True, type=bool)

        if date == "":
            date = get_default_year_and_month()

        year, month, day = do_split_date(date)

        item_list, amount = msg_dao.list_by_date(
            user_name, date, limit=MAX_LIST_LIMIT)
        message_list = convert_message_list_to_day_folder(
            item_list, date, True)
        
        kw = Storage()
        kw.tag = "log.date"
        kw.search_type = "message"
        kw.search_ext_dict = dict(tag="log.search")

        return xtemplate.render("message/page/message_list_by_day.html",
                                date=date,
                                year=year,
                                month=month,
                                message_list=message_list,
                                show_empty=show_empty,
                                show_back_btn=True,
                                month_size=count_month_size(message_list),
                                **kw)


class MessageRefreshHandler:

    @xauth.login_required("admin")
    def GET(self):
        refresh_key_amount()
        refresh_message_index()
        return "success"


class MessageKeywordAjaxHandler:

    @xauth.login_required()
    def POST(self):
        keyword = xutils.get_argument_str("keyword")
        action = xutils.get_argument_str("action")

        assert keyword != ""
        assert action != ""

        if action in ("mark", "unmark"):
            return self.do_mark_or_unmark(keyword, action)

        return dict(code="404", message="指定动作不存在")

    def do_mark_or_unmark(self, keyword, action):
        user_name = xauth.current_name_str()
        tag_info = msg_dao.MsgTagInfoDao.get_or_create(user=user_name, content=keyword)
        assert tag_info != None

        if action == "unmark":
            tag_info.is_marked = False
        else:
            tag_info.is_marked = True

        msg_dao.MsgTagInfoDao.update(tag_info)
        
        return dict(code="success")

xutils.register_func("message.process_message", process_message)
xutils.register_func("message.get_current_message_stat",
                     get_current_message_stat)
xutils.register_func("url:/message/log", MessageLogHandler)


MSG_RULES = [
    CalendarRule(r"(\d+)年(\d+)月(\d+)日"),
]

class CreateCommentHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument_str("id")
        content = xutils.get_argument_str("content")

        if content == "":
            return webutil.FailedResult(message="备注内容不能为空")

        user_name = xauth.current_name_str()
        msg = dao.get_message_by_id(id, user_name=user_name)
        if msg == None:
            return webutil.FailedResult(message="随手记不存在")
        comment = dao.MessageComment()
        comment.content = content
        msg.comments.append(comment)
        
        dao.update_message(msg)
        return webutil.SuccessResult()


class DeleteCommentHandler:
    
    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument_str("id")
        time_str = xutils.get_argument_str("time")

        if time_str == "":
            return webutil.FailedResult(message="备注时间不能为空")
        user_name = xauth.current_name_str()
        msg = dao.get_message_by_id(id, user_name=user_name)
        if msg == None:
            return webutil.FailedResult(message="随手记不存在")
        
        new_comments = []
        for comment in msg.comments:
            if comment.get("time") != time_str:
                new_comments.append(comment)
        
        msg.comments = new_comments
        dao.update_message(msg)
        return webutil.SuccessResult()
    
class ListCommentHandler:
    
    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument_str("id")
        user_name = xauth.current_name_str()
        msg = dao.get_message_by_id(id, user_name=user_name)
        if msg == None:
            return webutil.FailedResult(message="随手记不存在")
        
        comments = list(reversed(msg.comments))
        return webutil.SuccessResult(data=comments)


xurls = (
    r"/message", MessageHandler,
    r"/message/calendar", CalendarHandler,
    r"/message/todo", TodoHandler,
    r"/message/log", MessageLogHandler,
    r"/message/done", TodoDoneHandler,
    r"/message/canceled", TodoCanceledHandler,
    r"/message/detail", MessageDetailAjaxHandler,

    # 日记
    r"/message/dairy", MessageListByDayHandler,
    r"/message/list_by_day", MessageListByDayHandler,

    r"/message/refresh", MessageRefreshHandler,
    
    # Ajax处理
    r"/message/list", ListAjaxHandler,
    r"/message/date", DateAjaxHandler,
    r"/message/stat", StatAjaxHandler,
    r"/message/save", SaveAjaxHandler,
    r"/message/delete", DeleteAjaxHandler,
    r"/message/update", SaveAjaxHandler,
    r"/message/open", OpenMessageAjaxHandler,
    r"/message/finish", FinishMessageAjaxHandler,
    r"/message/touch", TouchAjaxHandler,
    r"/message/tag", UpdateTagAjaxHandler,
    r"/message/keyword", MessageKeywordAjaxHandler,
    r"/message/comment/create", CreateCommentHandler,
    r"/message/comment/delete", DeleteCommentHandler,
    r"/message/comment/list", ListCommentHandler,
)
