# -*- coding:utf-8 -*-
# Created by xupingmao on 2017/05/29
# @since 2017/08/04
# @modified 2022/04/11 23:23:57

"""短消息处理，比如任务、备忘、临时文件等等

tag: 短消息的类型
key/keyword: 短消息关键字

"""
import time
import math
import xutils
import xauth
import xconfig
import xmanager
import xtemplate
from xutils import BaseRule, Storage, functions, u, SearchResult
from xutils import dateutil
from xtemplate import T
from xutils import netutil
from xutils.functions import safe_list
from handlers.message.message_utils import (
    list_task_tags,
    process_message,
    filter_key,
    filter_msg_list_by_key,
    format_message_stat,
    MessageListParser,
    get_remote_ip,
    get_length,
    get_tags_from_message_list,
    get_similar_key,
    is_system_tag,
    do_split_date,
    success,
    failure,
    convert_message_list_to_day_folder,
    count_month_size,
)

from .message_utils import sort_keywords_by_marked
from . import dao
from handlers.message import message_utils
from xutils.db.lock import RecordLock

MSG_DAO = xutils.DAO("message")
# 消息处理规则
MSG_RULES = []
# 默认的标签
DEFAULT_TAG = "log"
MAX_LIST_LIMIT = 1000
# 系统标签
SYSTEM_TAG_TUPLE = ("book", "people", "file", "phone", "link")

LIST_VIEW_TPL = "message/page/message_list_view.html"


@xmanager.searchable()
def on_search_message(ctx):
    if ctx.search_message is False:
        return

    key = ctx.key
    touch_key_by_content(ctx.user_name, 'key', key)
    max_len = xconfig.SEARCH_SUMMARY_LEN

    messages, count = dao.search_message(ctx.user_name, key, 0, 3)
    search_result = []
    for message in messages:
        item = SearchResult()
        if message.content != None and len(message.content) > max_len:
            message.content = message.content[:max_len] + "......"
        process_message(message)
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


def get_current_message_stat():
    user_name = xauth.current_name()
    message_stat = MSG_DAO.get_message_stat(user_name)
    return format_message_stat(message_stat)


def update_keyword_amount(message, user_name, key):
    msg_list, amount = dao.search_message(user_name, key, 0, 1)
    message.amount = amount
    MSG_DAO.update(message)
    xutils.log("[message.refresh] user:%s,key:%s,amount:%s" %
               (user_name, key, amount))


@xutils.timeit(name="message.refresh", logfile=True)
def refresh_key_amount():
    for user_info in xauth.iter_user(limit=-1):
        user_name = user_info.name
        msg_list, amount = MSG_DAO.list_by_tag(user_name, "key", 0, -1)
        for index, message in enumerate(msg_list):
            key = message.content
            update_keyword_amount(message, user_name, key)


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
    process_message(msg_item)

    if get_length(msg_item.keywords) == 0:
        msg_item.no_tag = True
        msg_item.keywords = None
        MSG_DAO.update(msg_item)
    after_upsert_async(msg_item)


@xutils.async_func_deco()
def after_upsert_async(msg_item):
    """插入或者更新异步处理"""
    user_name = msg_item.user

    for keyword in safe_list(msg_item.keywords):
        message = get_or_create_keyword(user_name, keyword, msg_item.ip)
        update_keyword_amount(message, user_name, keyword)


def is_marked_keyword(user_name, keyword):
    obj = MSG_DAO.get_by_content(user_name, "key", keyword)
    return obj != None and obj.is_marked

# class


class SearchContext:

    def __init__(self, key):
        self.key = key


class ListAjaxHandler:

    @xauth.login_required()
    def GET(self):
        pagesize = xutils.get_argument("pagesize", xconfig.PAGE_SIZE, type=int)
        page = xutils.get_argument("page", 1, type=int)
        tag = xutils.get_argument("tag", "task")
        format = xutils.get_argument("format")
        offset = get_offset_from_page(page, pagesize)

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
        key = xutils.get_argument("key", "")
        date = xutils.get_argument("date", "")
        filter_date = xutils.get_argument("filterDate", "")

        if (tag == "search") or (key != "" and key != None):
            # 搜索
            return self.do_search(user_name, key, offset, pagesize)

        if tag == "date":
            # 日期
            return self.do_list_by_date(user_name, date, offset, pagesize)

        if filter_date != "":
            return self.do_list_by_date(user_name, filter_date, offset, pagesize)

        if tag == "task":
            return self.do_list_task(user_name, offset, pagesize)

        if tag == "key":
            return self.do_list_key(user_name, offset, pagesize)

        list_func = xutils.lookup_func("message.list_%s" % tag)
        if list_func != None:
            return list_func(user_name, offset, pagesize)
        else:
            return MSG_DAO.list_by_tag(user_name, tag, offset, pagesize)

    def do_get_html(self, chatlist, page, page_max, tag="task"):
        show_todo_check = True
        show_edit_btn = True
        show_to_log_btn = False
        display_tag = xutils.get_argument("displayTag", "")
        date = xutils.get_argument("date", "")
        key = xutils.get_argument("key", "")
        filter_key = xutils.get_argument("filterKey", "")
        orderby = xutils.get_argument("orderby", "")
        p = xutils.get_argument("p", "")
        xutils.get_argument("show_marked_tag", "true", type=bool)

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
            item_list=chatlist
        )

        return xtemplate.render(template_file, **kw)

    def do_search(self, user_name, key, offset, pagesize):
        # 搜索
        search_tags = None
        no_tag = False

        input_search_tags = xutils.get_argument("searchTags", "")
        input_no_tag = xutils.get_argument("noTag", "false")
        p = xutils.get_argument("p", "")
        date = xutils.get_argument("date", "")

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

        searcher = SearchHandler()
        return searcher.get_ajax_data(user_name=user_name, key=key, offset=offset,
                                      limit=pagesize, search_tags=search_tags,
                                      no_tag=no_tag, date=date)

    def do_list_task(self, user_name, offset, limit):
        p = xutils.get_argument("p", "")
        filter_key = xutils.get_argument("filterKey", "")
        status = xutils.get_argument("status", "")

        if p == "done":
            return MSG_DAO.list_task_done(user_name, offset, limit)

        if filter_key != "":
            msg_list, amount = MSG_DAO.list_task(
                user_name, offset=0, limit=MAX_LIST_LIMIT)
            msg_list = filter_msg_list_by_key(msg_list, filter_key)
            return msg_list[offset:offset+limit], len(msg_list)
        else:
            return MSG_DAO.list_task(user_name, offset, limit)

    def do_list_by_date(self, user_name, date, offset, pagesize):
        filter_key = xutils.get_argument("filterKey", "")

        if filter_key != "":
            msg_list, amount = MSG_DAO.list_by_date(
                user_name, date, 0, MAX_LIST_LIMIT)
            msg_list = filter_msg_list_by_key(msg_list, filter_key)
            return msg_list[offset:offset+pagesize], len(msg_list)
        else:
            return MSG_DAO.list_by_date(user_name, date, offset, pagesize)

    def do_list_key(self, user_name, offset, limit):
        orderby = xutils.get_argument("orderby", "")
        msg_list, amount = MSG_DAO.list_by_tag(
            user_name, "key", 0, MAX_LIST_LIMIT)
        p = message_utils.MessageKeyWordProcessor(msg_list)
        p.process()
        p.sort(orderby)

        return msg_list[offset:offset+limit], len(msg_list)


def update_message_status(id, status):
    user_name = xauth.current_name()
    data = MSG_DAO.get_by_id(id)
    if data and data.user == user_name:
        data.status = status
        data.mtime = xutils.format_datetime()

        MSG_DAO.update(data)
        MSG_DAO.refresh_message_stat(user_name)

        event = Storage(id=id, user=user_name,
                        status=status, content=data.content)
        xmanager.fire("message.updated", event)
        xmanager.fire("message.update", event)
        return dict(code="success")
    else:
        return failure(message="无操作权限")


def update_message_content(id, user_name, content):
    data = MSG_DAO.get_by_id(id)
    if data and data.user == user_name:
        # 先保存历史
        MSG_DAO.add_history(data)

        data.content = content
        data.mtime = xutils.format_datetime()
        data.version = data.get('version', 0) + 1
        MSG_DAO.update(data)

        xmanager.fire("message.update", dict(
            id=id, user=user_name, content=content))

        after_message_create_or_update(data)


def create_done_message(old_message):
    old_id = old_message['id']

    new_message = Storage()
    new_message['content'] = ''
    new_message['ref'] = old_id
    new_message['tag'] = 'done'
    new_message['user'] = old_message['user']
    new_message['ctime'] = xutils.format_datetime()

    MSG_DAO.create(**new_message)


def update_message_tag(id, tag):
    user_name = xauth.current_name()
    data = MSG_DAO.get_by_id(id)
    if data and data.user == user_name:
        # 修复status数据，全部采用tag
        if 'status' in data:
            del data['status']
        data.tag = tag
        data.mtime = xutils.format_datetime()
        if tag == "done":
            data.done_time = xutils.format_datetime()
            # 任务完成时除了标记原来任务的完成时间，还要新建一条消息
            create_done_message(data)

        MSG_DAO.update(data)
        MSG_DAO.refresh_message_stat(user_name)
        xmanager.fire("message.updated", Storage(
            id=id, user=user_name, tag=tag, content=data.content))

    return dict(code="success")


class FinishMessageAjaxHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("id")
        if id == "":
            return
        return update_message_tag(id, "done")


class OpenMessageAjaxHandler:

    def POST(self):
        id = xutils.get_argument("id")
        if id == "":
            return
        return update_message_tag(id, "task")


class UpdateTagAjaxHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("id")
        tag = xutils.get_argument("tag")
        if id == "":
            return failure(code="404", message="id为空")

        if tag in ("task", "cron", "log", "key", "done"):
            return update_message_tag(id, tag)
        else:
            return failure(message="invalid tag(%s)" % tag)


class UpdateStatusAjaxHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("id")
        status = xutils.get_argument("status", type=int)
        return update_message_status(id, status)


class TouchAjaxHandler:

    def do_touch_by_id(self, id):
        msg = MSG_DAO.get_by_id(id)
        if msg is None:
            return failure(message="message not found, id:%s" % id)
        if msg.user != xauth.current_name():
            return failure(message="not authorized")
        msg.mtime = xutils.format_datetime()
        MSG_DAO.update(msg)
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

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("id")
        if id == "":
            return failure(message="id为空")

        try:
            msg = MSG_DAO.get_by_id(id)
        except:
            return failure(message="删除失败")

        if msg is None:
            return dict(code="fail", message="data not exists")

        if msg.user != xauth.current_name():
            return dict(code="fail", message="no permission")

        # 先保存历史
        MSG_DAO.add_history(msg)

        # 删除并刷新统计信息
        MSG_DAO.delete(id)
        MSG_DAO.refresh_message_stat(msg.user)
        return dict(code="success")


class CalendarRule(BaseRule):

    def execute(self, ctx, date, month, day):
        print(date, month, day)
        ctx.type = "calendar"


def create_message(user_name, tag, content, ip):
    assert isinstance(user_name, str)
    assert isinstance(tag, str)
    assert isinstance(content, str)

    if tag == "todo":
        tag = "task"

    if tag == "key":
        content = filter_key(content)

    date = xutils.get_argument("date", "")
    content = content.strip()
    ctime = xutils.format_datetime()

    message = Storage()
    message.user = user_name
    message.tag = tag
    message.ip = ip
    message.date = date
    message.ctime = ctime
    message.mtime = ctime
    message.content = content

    id = MSG_DAO.create(**message)

    message.id = id

    MSG_DAO.refresh_message_stat(user_name)

    created_msg = MSG_DAO.get_by_id(id)
    assert created_msg != None
    after_message_create_or_update(created_msg)

    create_event = dict(id=id, user=user_name, content=content, ctime=ctime)
    xmanager.fire('message.add', create_event)
    xmanager.fire('message.create', create_event)

    return message


def check_content_for_update(user_name, tag, content):
    if tag == 'key':
        return MSG_DAO.get_by_content(user_name, tag, content)
    return None


def touch_key_by_content(user_name, tag, content):
    item = check_content_for_update(user_name, tag, content)
    if item != None:
        item.mtime = xutils.format_datetime()
        if item.visit_cnt is None:
            item.visit_cnt = 0
        item.visit_cnt += 1

        MSG_DAO.update(item)
    return item


def get_or_create_keyword(user_name, content, ip):
    with RecordLock(user_name):
        item = MSG_DAO.get_by_content(user_name, "key", content)
        if item != None:
            return item
        return create_message(user_name, "key", content, ip)


def apply_rules(user_name, id, tag, content):
    global MSG_RULES
    ctx = Storage(id=id, content=content, user=user_name, type="")
    for rule in MSG_RULES:
        rule.match_execute(ctx, content)


class SaveAjaxHandler:

    @xauth.login_required()
    def do_post(self):
        id = xutils.get_argument("id")
        content = xutils.get_argument("content")
        tag = xutils.get_argument("tag", DEFAULT_TAG)
        location = xutils.get_argument("location", "")
        user_name = xauth.get_current_name()
        ip = get_remote_ip()

        if content == None or content == "":
            return dict(code="fail", message="输入内容为空!")

        # 对消息进行语义分析处理，后期优化把所有规则统一管理起来
        apply_rules(user_name, id, tag, content)

        if id == "" or id is None:
            item = touch_key_by_content(user_name, tag, content)
            if item != None:
                message = item
            else:
                message = create_message(user_name, tag, content, ip)
            return dict(code="success", data=message)
        else:
            update_message_content(id, user_name, content)
        return dict(code="success", data=dict(id=id))

    def POST(self):
        try:
            return self.do_post()
        except Exception as e:
            xutils.print_exc()
            return dict(code="fail", message=str(e))


class DateAjaxHandler:

    @xauth.login_required()
    def GET(self):
        date = xutils.get_argument("date", "")
        page = xutils.get_argument("page", 1, type=int)
        user_name = xauth.current_name()

        if date == "":
            return xtemplate.render("error.html", error="date参数为空")

        offset = get_offset_from_page(page)
        limit = xconfig.PAGE_SIZE

        msg_list, msg_count = MSG_DAO.list_by_date(
            user_name, date, offset, limit)

        parser = MessageListParser(msg_list)
        parser.parse()

        page_max = get_page_max(msg_count, xconfig.PAGE_SIZE)

        return xtemplate.render("message/ajax/message_ajax.html",
                                page_max=page_max,
                                page=page,
                                page_url="?date=%s&page=" % date,
                                item_list=msg_list)


class MessageListHandler:

    @xauth.login_required()
    def do_get(self, tag="task"):
        user = xauth.current_name()
        key = xutils.get_argument("key", "")
        from_ = xutils.get_argument("from", "")
        type_ = xutils.get_argument("type", "")
        show_tab = xutils.get_argument(
            "show_tab", default_value=True, type=bool)
        op = xutils.get_argument("op", "")
        date = xutils.get_argument("date", "")

        # 记录日志
        xmanager.add_visit_log(user, "/message?tag=%s" % tag)

        if tag == "month_tags":
            return self.do_view_month_tags()

        if tag == "date":
            return self.do_view_by_date(date)

        if tag == "key" and op == "select":
            return self.do_select_key()

        if tag == "key":
            return self.get_log_tags_page()

        if tag == "task":
            return self.get_task_page()

        if tag == "task_tags":
            return self.get_task_taglist_page()

        if tag == "search" or type_ == "search":
            return SearchHandler().get_page()

        return self.get_log_page()

    def do_select_key(self):
        user_name = xauth.current_name()
        offset = 0
        msg_list, amount = MSG_DAO.list_by_tag(
            user_name, "key", offset, MAX_LIST_LIMIT)

        return xtemplate.render("message/page/message_tag_select.html",
                                msg_list=msg_list,
                                show_nav=False)

    def get_log_tags_page(self):
        orderby = xutils.get_argument("orderby", "")

        kw = dict(
            tag="key",
            search_type="message",
            show_tag_btn=False,
            show_sub_link=True,
            show_attachment_btn=False,
            show_system_tag=True,
            message_placeholder="添加标签/关键字/话题",
            show_side_tags=False,
        )

        return xtemplate.render("message/page/message_list_view.html", **kw)

    def get_system_tag_page(self, tag):
        kw = Storage(
            message_tag=tag,
            search_type="message",
            show_input_box=False,
            show_side_tags=False,
        )

        return xtemplate.render("message/page/message_list_view.html", **kw)

    def get_task_kw(self):
        kw = Storage()
        kw.title = T("待办任务")
        kw.html_title = T("待办任务")
        kw.search_type = "task"
        kw.show_back_btn = True
        kw.tag = "task"
        kw.message_placeholder = T("添加待办任务")
        kw.message_tab = "task"
        return kw

    def get_task_create_page(self):
        kw = self.get_task_kw()
        kw.show_input_box = True
        kw.show_system_tag = False
        kw.side_tags = list_task_tags(xauth.current_name())
        kw.side_tag_tab_key = "filterKey"

        return xtemplate.render("message/page/message_list_view.html", **kw)

    def get_task_by_keyword_page(self, filter_key):
        user_name = xauth.current_name()
        kw = self.get_task_kw()
        kw.message_tag = "task"
        kw.show_system_tag = False
        kw.show_sub_link = False
        kw.show_input_box = True
        kw.side_tag_tab_key = "filterKey"

        if filter_key != "$no_tag":
            kw.show_keyword_info = True

        kw.is_keyword_marked = is_marked_keyword(user_name, filter_key)
        kw.keyword = filter_key
        kw.side_tags = list_task_tags(user_name)

        if not is_system_tag(filter_key):
            kw.default_content = filter_key

        return xtemplate.render("message/page/message_list_view.html", **kw)

    def get_task_done_page(self):
        kw = self.get_task_kw()
        kw.show_system_tag = False
        kw.show_input_box = False
        kw.show_side_tags = False
        return xtemplate.render("message/page/message_list_view.html", **kw)

    def get_task_page(self):
        filter_key = xutils.get_argument("filterKey", "")
        page_name = xutils.get_argument("p", "")

        if page_name == "create":
            return self.get_task_create_page()

        if page_name == "done":
            return self.get_task_done_page()

        if page_name == "taglist":
            return self.get_task_taglist_page()

        if filter_key != "":
            return self.get_task_by_keyword_page(filter_key)
        else:
            # 任务的首页
            return self.get_task_home_page()

    def get_task_home_page(self):
        return self.get_task_create_page()

    def get_task_taglist_page(self):
        user_name = xauth.current_name()
        msg_list, amount = MSG_DAO.list_task(user_name, 0, -1)

        tag_list = get_tags_from_message_list(
            msg_list, "task", display_tag="taglist")

        for tag in tag_list:
            tag.is_marked = is_marked_keyword(user_name, tag.name)

        sort_keywords_by_marked(tag_list)

        kw = self.get_task_kw()
        kw.message_tag = "task"
        kw.tag_list = tag_list
        kw.html_title = T("待办任务")
        kw.message_placeholder = T("添加待办任务")

        kw.show_sub_link = False
        kw.show_task_create_entry = True
        kw.show_task_done_entry = True

        return xtemplate.render("message/page/message_tag_view.html", **kw)

    def do_view_month_tags(self):
        user_name = xauth.current_name()
        date = xutils.get_argument("date", "")

        year, month, mday = do_split_date(date)

        msg_list, amount = MSG_DAO.list_by_date(
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

        if p == "taglist":
            return self.get_log_tags_page()

        if p == "date":
            p2 = xutils.get_argument("p2", "")
            if p2 == "detail":
                date = xutils.get_argument("date", "")
                return self.do_view_by_date(date)
            return MessageListByDayHandler().GET()

        if p in SYSTEM_TAG_TUPLE:
            return self.get_system_tag_page(p)

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
            side_tags=MSG_DAO.list_hot_tags(user_name, 20),
        )

        if key != "" or input_tag == "search":
            # 搜索操作
            kw["title"] = T("随手记-搜索")
            kw["html_title"] = T("随手记-搜索")
            kw.show_back_btn = True
            kw.show_keyword_info = True
            kw.keyword = key
            kw.is_keyword_marked = is_marked_keyword(user_name, key)

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
        tag = xutils.get_argument("tag")
        return self.do_get(tag)


class MessageEditHandler:

    @xauth.login_required()
    def GET(self):
        id = xutils.get_argument("id")
        detail = MSG_DAO.get_by_id(id)

        if detail.ref != None:
            detail = MSG_DAO.get_by_id(detail.ref)

        return xtemplate.render("message/page/message_edit.html",
                                show_nav=False,
                                detail=detail)


class CalendarHandler:

    @xauth.login_required()
    def GET(self):
        user = xauth.current_name()
        date = xutils.get_argument("date")

        year, month, mday = do_split_date(date)

        date = "%s-%02d" % (year, month)

        return xtemplate.render("message/page/message_calendar.html",
                                tag="date",
                                year=year,
                                month=month,
                                date=date,
                                html_title=T("随手记"),
                                search_type="message")


class StatAjaxHandler:

    @xauth.login_required()
    def GET(self):
        user = xauth.current_name()
        stat = MSG_DAO.get_message_stat(user)
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
        message_stat = MSG_DAO.get_message_stat(user_name)
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

        item_list, amount = MSG_DAO.list_by_date(
            user_name, date, limit=MAX_LIST_LIMIT)
        message_list = convert_message_list_to_day_folder(
            item_list, date, True)

        return xtemplate.render("message/page/message_list_by_day.html",
                                date=date,
                                year=year,
                                month=month,
                                message_list=message_list,
                                show_empty=show_empty,
                                show_back_btn=True,
                                search_type="message",
                                month_size=count_month_size(message_list),
                                tag="date")


class MessageRefreshHandler:

    @xauth.login_required("admin")
    def GET(self):
        refresh_key_amount()
        refresh_message_index()
        return "success"


class MessageKeywordAjaxHandler:

    @xauth.login_required()
    def POST(self):
        keyword = xutils.get_argument("keyword", "")
        action = xutils.get_argument("action", "")

        assert keyword != ""
        assert action != ""

        if action in ("mark", "unmark"):
            return self.do_mark_or_unmark(keyword, action)

        return dict(code="404", message="指定动作不存在")

    def do_mark_or_unmark(self, keyword, action):
        user_name = xauth.current_name()
        
        with RecordLock(user_name):
            key_obj = MSG_DAO.get_by_content(user_name, "key", keyword)

            if key_obj == None:
                # 不存在，创建新的标签
                ip = get_remote_ip()
                key_obj = create_message(user_name, "key", keyword, ip)

            if action == "unmark":
                key_obj.is_marked = None
            else:
                key_obj.is_marked = True

            MSG_DAO.update(key_obj)
        
        return dict(code="success")


class SearchHandler:
    """搜索逻辑处理"""

    def get_page(self):
        user_name = xauth.current_name()
        key = xutils.get_argument("key", "")

        kw = Storage()
        kw.tag = "search"
        kw.key = key
        kw.keyword = key
        kw.default_content = message_utils.filter_key(key)
        kw.side_tags = MSG_DAO.list_hot_tags(user_name, 20)
        kw.create_tag = self.get_create_tag()

        return xtemplate.render("message/page/message_search.html", **kw)

    def get_ajax_data(self, *, user_name=None, key=None, offset=0,
                      limit=20, search_tags=None, no_tag=False, date=""):
        start_time = time.time()
        chatlist, amount = dao.search_message(
            user_name, key, offset, limit,
            search_tags=search_tags, no_tag=no_tag, date=date)

        # 搜索扩展
        xmanager.fire("message.search", SearchContext(key))

        # 自动置顶
        touch_key_by_content(user_name, "key", key)
        touch_key_by_content(user_name, "key", get_similar_key(key))

        cost_time = functions.second_to_ms(time.time() - start_time)

        MSG_DAO.add_search_history(user_name, key, cost_time)

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


xutils.register_func("message.process_message", process_message)
xutils.register_func("message.get_current_message_stat",
                     get_current_message_stat)
xutils.register_func("url:/message/log", MessageLogHandler)


MSG_RULES = [
    CalendarRule(r"(\d+)年(\d+)月(\d+)日"),
]

xurls = (
    r"/message", MessageHandler,
    r"/message/calendar", CalendarHandler,
    r"/message/todo", TodoHandler,
    r"/message/log", MessageLogHandler,
    r"/message/done", TodoDoneHandler,
    r"/message/canceled", TodoCanceledHandler,
    r"/message/edit", MessageEditHandler,

    # 日记
    r"/message/dairy", MessageListByDayHandler,
    r"/message/list_by_day", MessageListByDayHandler,

    r"/message/refresh", MessageRefreshHandler,
    # Ajax处理
    r"/message/list", ListAjaxHandler,
    r"/message/date", DateAjaxHandler,
    r"/message/stat", StatAjaxHandler,
    r"/message/save", SaveAjaxHandler,
    r"/message/status", UpdateStatusAjaxHandler,
    r"/message/delete", DeleteAjaxHandler,
    r"/message/update", SaveAjaxHandler,
    r"/message/open", OpenMessageAjaxHandler,
    r"/message/finish", FinishMessageAjaxHandler,
    r"/message/touch", TouchAjaxHandler,
    r"/message/tag", UpdateTagAjaxHandler,
    r"/message/keyword", MessageKeywordAjaxHandler,
)
