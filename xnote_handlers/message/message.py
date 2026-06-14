# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2017-05-29 00:00:00
@LastEditors  : xupingmao
@LastEditTime : 2024-08-24 22:37:09
@FilePath     : /xnote/handlers/message/message.py
@Description  : 描述
"""

"""短消息处理，比如任务、备忘、临时文件等等
tag: 短消息的类型
key/keyword: 短消息关键字
"""
import web
import time
import math
import xutils
import xnote_handlers.message.dao as msg_dao
import logging

from typing import List, Tuple
from xnote.core import xauth, xconfig, xmanager, xtemplate
from xutils import BaseRule, Storage
from xnote.core.xtemplate import T
from xutils import netutil, webutil
from xutils.textutil import quote
from xnote_handlers.message.message_task import TaskListHandler
from xnote_handlers.message.message_date import MessageDateHandler
from xnote_handlers.message.message_date import MessageListByDayHandler
from xnote_handlers.message.message_log import LogPageHandler
from xnote_handlers.message.message_model import MessageTagEnum
from xnote.core import xnote_event
from xnote.plugin import TabBox

from xnote_handlers.message.message_utils import (
    process_message,
    filter_msg_list_by_key,
    format_message_stat,
    MessageListParser,
    get_remote_ip,
    get_length,
    do_split_date,
    success,
    failure,
    touch_key_by_content,
    TagHelper,
)

from . import dao, message_tag, message_search
from .dao import MessageDao
from xnote_handlers.message import message_utils
from .message_model import MessageComment

MSG_DAO = xutils.DAO("message")
# 消息处理规则
MSG_RULES = []
# 默认的标签
DEFAULT_TAG = "log"
MAX_LIST_LIMIT = 1000
LIST_VIEW_TPL = "message/page/message_list_view.html"

def get_current_message_stat():
    user_name = xauth.current_name()
    message_stat = MessageDao.get_message_stat(user_name)
    return format_message_stat(message_stat)


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

    MessageDao.update_user_tags(msg_item)
    
    if get_length(msg_item.full_keywords) == 0:
        msg_item.no_tag = True
        msg_item.keywords = None
        MessageDao.update(msg_item)
    
    after_upsert(msg_item)

def after_message_delete(msg_item):
    process_message(msg_item)
    after_upsert(msg_item)

def after_upsert(msg_item: msg_dao.MessageDO):
    """插入或者更新异步处理"""
    message_tag.update_tag_amount_by_msg(msg_item)

class ListAjaxHandler:

    def get_argument_tag(self):
        sys_tag = xutils.get_argument_str("sys_tag")
        if sys_tag != "":
            return sys_tag
        return xutils.get_argument_str("tag", "task")

    @xauth.login_required()
    def GET(self):
        pagesize = xutils.get_argument_int("pagesize", xconfig.PAGE_SIZE)
        page = xutils.get_argument_int("page", 1)
        tag = self.get_argument_tag()
        format = xutils.get_argument_str("format")
        offset = get_offset_from_page(page, pagesize)

        assert isinstance(tag, str)

        if tag == "key" or tag == "log.tags":
            return webutil.FailedResult(message="功能已迁移")

        user_name = xauth.current_name_str()
        chatlist, amount = self.do_list_message(
            user_name, tag, offset, pagesize)

        page_max = get_page_max(amount, pagesize)

        parser = MessageListParser(chatlist, tag=tag)
        parser.parse()
        chatlist = parser.get_message_list()

        if format == "html":
            return self.do_get_html(chatlist, page, page_total=amount, tag=tag, page_size=pagesize)
        
        result = webutil.SuccessResult(data=chatlist)
        result.keywords = parser.get_keywords()
        result.amount = amount
        result.page_max = page_max
        result.page_total = amount
        result.pagesize = pagesize
        result.current_user = xauth.current_name()
        return result

    def do_list_message(self, user_name, tag, offset, pagesize) -> Tuple[list, int]:
        key = xutils.get_argument_str("key", "")
        date = xutils.get_argument_str("date", "")
        filter_key = xutils.get_argument_str("filterKey", "")
        
        if filter_key:
            # 多标签搜索
            key = filter_key.replace(",", " ")
            return self.do_search(user_name, key, offset, pagesize, search_tags=["log"])

        if tag == "task.search":
            return self.do_search(user_name, key, offset, pagesize,search_tags=["task"])
        
        if tag == "done.search":
            return self.do_search(user_name, key, offset, pagesize, search_tags=["done"])

        if (tag in ("search", "log.search")) or (key != "" and key != None):
            # 搜索
            return self.do_search(user_name, key, offset, pagesize, search_tags=["log"])
        
        if tag == "log.date":
            return MessageDateHandler().do_list_by_date(
                user_name=user_name, date=date, offset=offset, limit=pagesize, tag="log")
        
        return msg_dao.list_by_tag(user_name, tag, offset, pagesize)

    def do_get_html(self, msg_list, page: int, page_total: int, tag="task", page_size = 20):
        show_todo_check = True
        show_edit_btn = True
        show_to_log_btn = False
        display_tag = xutils.get_argument("displayTag", "")
        date = xutils.get_argument("date", "")
        key = xutils.get_argument("key", "")
        filter_key = xutils.get_argument_str("filterKey", "")
        orderby = xutils.get_argument("orderby", "")
        p = xutils.get_argument("p", "")
        xutils.get_argument_bool("show_marked_tag", True)
        sys_tag = xutils.get_argument_str("sys_tag")

        show_edit_btn = (p != "done")

        if tag == "todo" or tag == "task":
            show_todo_check = True
            show_to_log_btn = True

        if tag == "done":
            show_to_log_btn = True

        if tag == "key":
            show_edit_btn = False

        params = dict(
            tag=tag,
            sys_tag=sys_tag,
            displayTag=display_tag,
            key=key,
            date=date,
            filterKey=filter_key,
            orderby=orderby,
            p=p,
        )

        kw = Storage(
            show_todo_check=show_todo_check,
            show_edit_btn=show_edit_btn,
            show_to_log_btn=show_to_log_btn,
            page=page,
            page_total = page_total,
            page_size = page_size,
            item_list=msg_list
        )

        return xtemplate.render("message/page/message_list_ajax.html", **kw)

    def do_search(self, user_name, key, offset, pagesize, search_tags=None):
        # 搜索
        input_search_tags = xutils.get_argument_str("searchTags")
        no_tag = xutils.get_argument_bool("noTag", False)
        p = xutils.get_argument_str("p", "")
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

        searcher = message_search.SearchHandler()
        return searcher.get_ajax_data(
            user_name=user_name, key=key, offset=offset,
            limit=pagesize, search_tags=search_tags,
            no_tag=no_tag, date=date)


def update_message_content(id: int, user_id: int, content, files: List[str] = [], date = ""):
    data = MessageDao.get_by_int_id(id)
    if data is None:
        return
    if data.user_id != user_id:
        return

    # 先保存历史
    MessageDao.add_history(data)
        
    data.content = content
    data.mtime = xutils.format_datetime()
    data.files = files
    data.version = data.get('version', 0) + 1
    if date and data.date != date:
        data._update_date = True
        data.ctime = date + " 00:00:00"
        data.date = date
        data.change_time = data.ctime
        
    MessageDao.update(data)

    event = xnote_event.MessageUpdateEvent()
    event.msg_id = data.int_id
    event.msg_key = data._key
    event.user_id = data.user_id
    event.content = content
    event.fire()

    after_message_create_or_update(data)


def update_message_tag(id:int, tag):
    """更新message的tag字段"""
    user_name = xauth.current_name()
    data = MessageDao.get_by_int_id(id)
    if data == None:
        return webutil.FailedResult(message="数据不存在")
    if data.user != user_name:
        return webutil.FailedResult(message="无权操作")
    
    # 修复status数据，全部采用tag
    data.pop("status", None)
    data.tag = tag
    data.mtime = xutils.format_datetime()
    data.change_time = data.mtime
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
        if ref:
            origin_data = MessageDao.get_by_full_key(ref)
            if origin_data != None:
                # 更新原始任务后删除当前的完成记录
                origin_data.append_comment("$reopen_task$")
                MessageDao.update_tag(origin_data, tag)
                MessageDao.delete_by_int_id(data.int_id)
                need_update = False
        
    if need_update:    
        MessageDao.update_tag(data, tag)

    event = xnote_event.MessageEvent(msg_key=data._key, user_id=data.user_id, tag=tag, content=data.content)
    event.fire()

    return webutil.SuccessResult()


class FinishMessageAjaxHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument_int("id")
        if id == 0:
            return
        return update_message_tag(id, "done")


class OpenMessageAjaxHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument_int("id")
        if id == 0:
            return
        return update_message_tag(id, "task")



class TouchAjaxHandler:

    def do_touch_by_id(self, id):
        msg = MessageDao.get_by_full_key(id)
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
        if msg.user_id != xauth.current_user_id():
            return webutil.FailedResult(code="fail", message="no permission")

        # 先保存历史
        MessageDao.add_history(msg)

        # 删除并刷新统计信息
        MessageDao.delete_by_int_id(msg.int_id)
        if msg.tag == "done" and msg.ref != None:
            MessageDao.delete_by_key(msg.ref)
            
        MessageDao.refresh_message_stat(msg.user, [msg.tag])
        after_message_delete(msg)

        return webutil.SuccessResult()
    
    def delete_tag(self, tag_info: msg_dao.MsgTagInfo):
        if tag_info.user_id != xauth.current_user_id():
            return webutil.FailedResult(message="no permission")
        
        msg_dao.MsgTagInfoDao.delete(tag_info)
        return webutil.SuccessResult()

    @xauth.login_required()
    def POST(self):
        int_id = xutils.get_argument_int("id")
        if int_id == 0:
            return failure(message="id为空")

        try:
            msg = MessageDao.get_by_int_id(int_id)
            if msg != None:
                return self.delete_msg(msg)
            return webutil.FailedResult(message="数据不存在")
        except:
            xutils.print_exc()
            return webutil.FailedResult(message="删除失败")


class CalendarRule(BaseRule):

    def execute(self, ctx, date, month, day):
        print(date, month, day)
        ctx.type = "calendar"


def create_message(user_name, tag, content, ip, files: List[str] = []):
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
    message.change_time = ctime
    message.files = files
    
    msg_id = MessageDao.create(message)
    MessageDao.refresh_message_stat(user_name, [message.tag])

    created_msg = MessageDao.get_by_int_id(msg_id)
    assert created_msg != None
    
    after_message_create_or_update(created_msg)

    create_event = dict(id=id, user=user_name, content=content, ctime=ctime)
    xmanager.fire('message.add', create_event)
    xmanager.fire('message.create', create_event)

    return message

def get_or_create_keyword(user_id=0, content="", ip=""):
    return msg_dao.MsgTagInfoDao.get_or_create(user_id, content)

class SaveAjaxHandler:

    def apply_rules(self, user_name, id, tag, content):
        global MSG_RULES
        ctx = Storage(id=id, content=content, user=user_name, type="")
        for rule in MSG_RULES:
            rule.match_execute(ctx, content)

    @xauth.login_required()
    def do_post(self):
        msg_id = xutils.get_argument_int("id")
        content = xutils.get_argument_str("content")
        tag = xutils.get_argument_str("tag", DEFAULT_TAG)
        location = xutils.get_argument_str("location", "")
        files = xutils.get_list_argument("files[]")
        user_name = xauth.get_current_name()
        user_id = xauth.current_user_id()
        ip = get_remote_ip()
        date = xutils.get_argument_str("date")

        if content == "" and len(files) == 0:
            return webutil.FailedResult(code="fail", message="输入内容为空!")
        
        tag = TagHelper.get_create_tag(tag)

        # 对消息进行语义分析处理，后期优化把所有规则统一管理起来
        self.apply_rules(user_name, id, tag, content)

        if msg_id == 0:
            message = create_message(user_name, tag, content, ip, files)
            return webutil.SuccessResult(data=message)
        else:
            update_message_content(msg_id, user_id, content, files, date = date)
        return webutil.SuccessResult(data=dict(id=msg_id))

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
        page = xutils.get_argument_int("page", 1)
        filter_key = xutils.get_argument_str("filterKey")
        user_id = xauth.current_user_id()
        tag = xutils.get_argument_str("tag", "log")

        if date == "":
            return xtemplate.render("error.html", error="date参数为空")

        offset = get_offset_from_page(page)
        limit = xconfig.PAGE_SIZE

        msg_list, msg_count = message_utils.list_by_date_and_key(
            user_id=user_id, 
            month=date, 
            offset=offset, 
            limit=limit, 
            filter_key=filter_key,
            tag=tag)

        parser = MessageListParser(msg_list)
        parser.parse()

        page_max = get_page_max(msg_count, xconfig.PAGE_SIZE)

        return xtemplate.render(
            "message/page/message_list_ajax.html",
            page_max=page_max,
            page=page,
            item_list=msg_list)


class MessagePageHandler:

    @xauth.login_required()
    def do_get(self, tag="task"):
        """随手记/待办的入口
        xxx_page 返回页面
        xxx_data 返回数据
        """
        user = xauth.current_name_str()
        type_ = xutils.get_argument("type", "")

        # 记录日志
        xmanager.add_visit_log(user, "/message?tag=%s" % tag)

        if tag == "api.tag_list":
            return self.get_tag_list()

        if tag == "task.tags":
            return TaskListHandler.get_task_taglist_page()

        if tag in ("search", "task.search", "done.search", "log.search") or type_ == "search":
            return message_search.SearchHandler().get_page()

        if tag == "key" or tag == "log.tags":
            return webutil.FailedResult(message="功能已迁移")
        
        return LogPageHandler().do_get()

    def get_tag_list(self):
        return message_tag.get_tag_list()

    def GET(self):
        tag = xutils.get_argument_str("tag")
        return self.do_get(tag)

class MessageEditDialogHandler:
    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument_int("id")
        user_name = xauth.current_name_str()
        user_id = xauth.current_user_id()
        detail = msg_dao.MessageDao.get_by_int_id(id, user_id=user_id)
        if detail == None:
            web.ctx.status = "404 Not Found"
            return "数据不存在"

        if detail.ref != None:
            detail = msg_dao.get_message_by_key(detail.ref, user_name=user_name)
        
        return xtemplate.render(
            "message/page/message_edit_dialog.html",
            detail = detail,
            submitBtnText="更新",
        )
    
class MessageCreateDialogHandler:
    @xauth.login_required()
    def GET(self):
        keyword = xutils.get_argument_str("keyword")
        tag = xutils.get_argument_str("tag")
        detail = msg_dao.MessageDO()
        detail.content = keyword
        detail.tag = tag
        return xtemplate.render(
            "message/page/message_edit_dialog.html",
            detail = detail,
            submitBtnText="创建",
        )

class StatAjaxHandler:

    @xauth.login_required()
    def GET(self):
        user = xauth.current_name_str()
        stat = msg_dao.get_message_stat(user)
        return format_message_stat(stat)


class MessageHandler(MessagePageHandler):
    pass


class MessageLogHandler(MessageHandler):

    def GET(self):
        return self.do_get("log")

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

        return webutil.FailedResult(code="404", message="指定动作不存在")

    def do_mark_or_unmark(self, keyword, action):
        user_id = xauth.current_user_id()
        tag_info = msg_dao.MsgTagInfoDao.get_or_create(user_id=user_id, content=keyword)
        assert tag_info != None

        if action == "unmark":
            tag_info.set_is_marked(False)
        else:
            tag_info.set_is_marked(True)

        msg_dao.MsgTagInfoDao.update(tag_info)
        
        return webutil.SuccessResult()

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
        id = xutils.get_argument_int("id")
        content = xutils.get_argument_str("content")

        if content == "":
            return webutil.FailedResult(message="备注内容不能为空")

        user_id = xauth.current_user_id()
        msg = dao.MessageDao.get_by_int_id(id, user_id=user_id)
        if msg == None:
            return webutil.FailedResult(message="随手记不存在")
        comment = MessageComment()
        comment.content = content
        msg.comments.append(comment)
        
        dao.update_message(msg)
        return webutil.SuccessResult()


class DeleteCommentHandler:
    
    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument_int("id")
        time_str = xutils.get_argument_str("time")

        if time_str == "":
            return webutil.FailedResult(message="备注时间不能为空")
        user_id = xauth.current_user_id()
        msg = dao.MessageDao.get_by_int_id(id, user_id = user_id)
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

    html = """
{% for value in comments %}
    <div class="todo-comment-row">
        <div class="content">{{value.content}}</div>
        <div class="comment-second">
            <span class="time">{{value.time}}</span>
            <a data-id="{{msg_id}}" data-time="{{value.time}}" 
                onclick="xnote.action.message.deleteComment(this)">删除</a>
        </div>
    </div>
{% end %}
"""

    _code = xtemplate.compile_template(html)
    
    @xauth.login_required()
    def POST(self):
        msg_id = xutils.get_argument_int("id")
        user_id = xauth.current_user_id()
        msg = dao.MessageDao.get_by_int_id(msg_id, user_id=user_id)
        if msg == None:
            return "随手记不存在"
        
        comments = list(reversed(msg.comments))
        return self._code.generate(comments = comments, msg_id=msg_id)

class ParseMessageHandler:

    @xauth.login_required()
    def POST(self):
        content = xutils.get_argument_str("content")
        msg_struct = message_utils.mark_text_to_tokens(content=content)
        return webutil.SuccessResult(msg_struct.__dict__)

    def GET(self):
        return self.POST()


class UpdateTagAjaxHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument_int("id")
        tag = xutils.get_argument_str("tag")
        if id == "":
            return webutil.FailedResult(code="404", message="id为空")

        if MessageTagEnum.is_first_tag_code(tag):
            return update_message_tag(id, tag)
        else:
            return webutil.FailedResult(message="无效的标签: %s" % tag)

xurls = (
    r"/message", MessagePageHandler,
    r"/message/log", MessageLogHandler,
    r"/message/edit_dialog", MessageEditDialogHandler,
    r"/message/create_dialog", MessageCreateDialogHandler,

    r"/message/refresh", MessageRefreshHandler,
    
    # Ajax处理
    r"/message/update_first_tag", UpdateTagAjaxHandler,
    r"/message/list", ListAjaxHandler,
    r"/message/date", DateAjaxHandler,
    r"/message/stat", StatAjaxHandler,
    r"/message/save", SaveAjaxHandler,
    r"/message/delete", DeleteAjaxHandler,
    r"/message/update", SaveAjaxHandler,
    r"/message/open", OpenMessageAjaxHandler,
    r"/message/finish", FinishMessageAjaxHandler,
    r"/message/touch", TouchAjaxHandler,
    r"/message/keyword", MessageKeywordAjaxHandler,
    r"/message/comment/create", CreateCommentHandler,
    r"/message/comment/delete", DeleteCommentHandler,
    r"/message/comment/list", ListCommentHandler,
    r"/message/parse", ParseMessageHandler,
)
