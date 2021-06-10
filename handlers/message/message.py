# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/29
# @since 2017/08/04
# @modified 2021/06/11 00:09:16

"""短消息处理，比如任务、备忘、临时文件等等"""
import time
import re
import math
import web
import xutils
import xtables
import xauth
import xconfig
import xmanager
import xtemplate
from xutils import BaseRule, Storage, dbutil, textutil, functions, u, SearchResult
from xutils import dateutil
from xtemplate import T
from xutils.textutil import escape_html, quote
from xutils.functions import Counter

MSG_DAO       = xutils.DAO("message")
DEFAULT_TAG   = "log"
TAG_TEXT_DICT = dict(
    done = "完成",
    cron = "定期",
    task = "任务",
    log  = "记事",
    key  = "话题",
    search = "话题",
)

LIST_LIMIT = 1000
# 系统标签
SYSTEM_TAG_TUPLE = ("book", "people", "file", "phone", "link")

def success():
    return dict(success = True, code = "success")

def failure(message, code = "fail"):
    return dict(success = False, code = code, message = message)

def build_search_url(keyword):
    key = quote(keyword)
    return u"/message?category=message&key=%s" % key


def build_search_html(content):
    fmt = u'<a href="/message?key=%s">%s</a>'
    return fmt % (xutils.encode_uri_component(content), xutils.html_escape(content))

def build_done_html(message):
    task = None
    done_time = message.done_time

    if message.ref != None:
        task = MSG_DAO.get_by_id(message.ref)

    if task != None:
        html, keywords = mark_text(task.content)
        message.html = u("完成任务:<br>&gt;&nbsp;") + html
        message.keywords = keywords
    elif done_time is None:
        done_time = message.mtime
        message.html += u("<br>------<br>完成于 %s") % done_time

def do_mark_topic(parser, key0):
    key = key0.lstrip("")
    key = key.rstrip("")
    quoted_key = textutil.quote(key)
    value = textutil.escape_html(key0)
    token = "<a class=\"link\" href=\"/message?key=%s\">%s</a>" % (quoted_key, value)
    parser.tokens.append(token)


def mark_text(content):
    import xconfig
    from xutils.marked_text_parser import TextParser
    from xutils.marked_text_parser import set_img_file_ext
    # 设置图片文集后缀
    set_img_file_ext(xconfig.FS_IMG_EXT_LIST)

    parser = TextParser()
    parser.set_topic_marker(do_mark_topic)

    tokens = parser.parse(content)
    return "".join(tokens), parser.keywords

def process_tag_message(message):
    message.html = build_search_html(message.content)

    if message.amount is None:
        message.amount = T("更新中...")

def process_message(message):
    if message.status == 0 or message.status == 50:
        # 兼容历史数据
        message.tag = "task"
    if message.status == 100:
        message.tag = "done"

    if message.tag == "cron":
        message.tag = "task"

    message.tag_text = TAG_TEXT_DICT.get(message.tag, message.tag)

    if message.content is None:
        message.content = ""
        return message

    if message.tag == "key" or message.tag == "search":
        process_tag_message(message)
    else:
        html, keywords = mark_text(message.content)
        message.html = html
        message.keywords = keywords

    if message.tag == "done":
        build_done_html(message)

    if message.keywords is None:
        message.keywords = set()
        
    return message


def fuzzy_item(item):
    item = item.replace("'", "''")
    return "'%%%s%%'" % item

def get_status_by_code(code):
    if code == "created":
        return 0
    if code == "suspended":
        return 50
    if code == "done":
        return 100
    return 0

def format_count(count):
    if count is None:
        return "0"
    if count >= 1000 and count < 1000000:
        return '%dk' % int(count / 1000)
    if count > 1000000:
        return '%dm' % int(count / 1000000)
    # 保持类型一致
    return str(count)

def format_message_stat(stat):
    stat.task_count = format_count(stat.task_count)
    stat.done_count = format_count(stat.done_count)
    stat.cron_count = format_count(stat.cron_count)
    stat.log_count  = format_count(stat.log_count)
    stat.search_count = format_count(stat.search_count)
    stat.key_count    = format_count(stat.key_count)
    return stat

@xmanager.searchable()
def on_search_message(ctx):
    key = ctx.key
    touch_key_by_content(ctx.user_name, 'key', key)

    messages, count = MSG_DAO.search(ctx.user_name, key, 0, 3)
    for message in messages:
        item = SearchResult()
        if message.content != None and len(message.content) > xconfig.SEARCH_SUMMARY_LEN:
            message.content = message.content[:xconfig.SEARCH_SUMMARY_LEN] + "......"
        process_message(message)
        item.name = u('记事 - ') + message.ctime
        item.html = message.html
        item.icon = "hide"
        ctx.messages.append(item)
        # print(message)
    if count > 3:
        more = SearchResult()
        more.name = "查看更多记事(%s)" % count
        more.url  = "/message?key=" + ctx.key
        ctx.messages.append(more)


def get_current_message_stat():
    user_name = xauth.current_name()
    return MSG_DAO.get_message_stat(user_name)


def do_split_date(date):
    year  = dateutil.get_current_year()
    month = dateutil.get_current_month()
    day   = dateutil.get_current_mday()

    if date == None or date == "":
        return year, month, day

    parts = date.split("-")
    if len(parts) >= 1:
        year = int(parts[0])
    if len(parts) >= 2:
        month = int(parts[1])
    if len(parts) >= 3:
        day = int(parts[2])
    return year, month, day


@xutils.timeit(name = "message.refresh", logfile = True)
def refresh_key_amount():
    for user_name in xauth.list_user_names():
        msg_list, amount = MSG_DAO.list_by_tag(user_name, "key", 0, -1)
        for index, message in enumerate(msg_list):
            key = message.content
            msg_list, amount = MSG_DAO.search(user_name, key, 0, 1)
            message.amount = amount
            MSG_DAO.update(message)
            xutils.log("[message.refresh] %s,user:%s,key:%s,amount:%s" % (index, user_name, key, amount))


def get_similar_key(key):
    assert key != None
    if key.startswith("#"):
        key = key.lstrip("#")
        key = key.rstrip("#")
        return key
    else:
        return "#" + key + "#"


def get_page_max(amount, pagesize = None):
    if pagesize is None:
        pagesize = xconfig.PAGE_SIZE
    return math.ceil(amount / pagesize)

def get_offset_from_page(page, pagesize = None):
    if pagesize is None:
        pagesize = xconfig.PAGE_SIZE

    offset = (page - 1) * pagesize
    return max(offset, 0)

def filter_msg_list_by_key(msg_list, filter_key):
    result = []

    for msg_item in msg_list:
        process_message(msg_item)

        if filter_key == "$no_tag" and len(msg_item.keywords) == 0:
            result.append(msg_item)
        elif filter_key in msg_item.keywords:
            result.append(msg_item)

    return result


def get_tags_from_message_list(msg_list, input_tag = "", input_date = ""):
    tag_counter = Counter()

    for msg_item in msg_list:
        process_message(msg_item)
        
        if msg_item.keywords is None:
            msg_item.keywords = set()

        if len(msg_item.keywords) == 0:
            tag_counter.incr("$no_tag")

        for tag in msg_item.keywords:
            tag_counter.incr(tag)

    tag_list = []
    for tag_name in tag_counter.dict:
        amount = tag_counter.get_count(tag_name)
        # url = "/message?searchTags=%s&key=%s" % (input_tag, textutil.encode_uri_component(tag_name))

        encoded_tag = textutil.encode_uri_component(tag_name)

        if input_date == "":
            url = "/message?tag=%s&filterKey=%s&filterDate=%s" % (input_tag, encoded_tag, input_date)
        else:
            url = "/message?tag=%s&date=%s&filterKey=%s" % (input_tag, input_date, encoded_tag)

        if tag_name == "$no_tag":
            tag_name = "<无标签>"
            # url = "/message?tag=search&searchTags=%s&noTag=true" % input_tag

        tag_item = Storage(name = tag_name, tag = input_tag, amount = amount, url = url)
        tag_list.append(tag_item)

    tag_list.sort(key = lambda x: x.amount, reverse = True)

    return tag_list

def get_length(item):
    if isinstance(item, (tuple, list, set, str)):
        return len(item)
    else:
        return -1

def after_message_create_or_update(msg_item):
    process_message(msg_item)

    if get_length(msg_item.keywords) == 0:
        msg_item.no_tag = True
        msg_item.keywords = None
        MSG_DAO.update(msg_item)

def function_and_class_split_line():
    pass

############  class

class SearchContext:

    def __init__(self, key):
        self.key = key

class MessageListParser(object):

    def __init__(self, chatlist):
        self.chatlist = chatlist

    def parse(self):
        self.do_process_message_list(self.chatlist)

    def do_process_message_list(self, message_list):
        keywords = set()
        for message in message_list:
            process_message(message)
            if message.keywords != None:
                keywords = message.keywords.union(keywords)
        
        self.keywords = []
        for word in keywords:
            keyword_info = Storage(name = word, url = build_search_url(word))
            self.keywords.append(keyword_info)

    def get_message_list(self):
        return self.chatlist

    def get_keywords(self):
        return self.keywords


class ListAjaxHandler:

    def do_get_html(self, chatlist, page, page_max, tag = "task"):
        show_todo_check = True
        show_edit_btn   = True
        show_to_log_btn = False
        display_tag     = xutils.get_argument("displayTag", "")
        date = xutils.get_argument("date", "")
        key  = xutils.get_argument("key", "")

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

        return xtemplate.render(template_file,
            show_todo_check = show_todo_check,
            show_edit_btn = show_edit_btn,
            show_to_log_btn = show_to_log_btn,
            page = page,
            page_url = "?tag=%s&displayTag=%s&date=%s&key=%s&page=" % (tag, display_tag, date, key),
            page_max = page_max,
            item_list = chatlist)

    def do_search(self, user_name, key, offset, pagesize):
        # 搜索
        search_tags = None
        no_tag = False

        input_search_tags = xutils.get_argument("searchTags", "")
        input_no_tag = xutils.get_argument("noTag", "false")

        if input_search_tags != "":
            search_tags = input_search_tags.split(",")

        if input_no_tag == "true":
            no_tag = True

        start_time = time.time()
        chatlist, amount = MSG_DAO.search(user_name, key, offset, pagesize, search_tags, no_tag = no_tag)

        # 搜索扩展
        xmanager.fire("message.search", SearchContext(key))

        # 自动置顶
        touch_key_by_content(user_name, "key", key)
        touch_key_by_content(user_name, "key", get_similar_key(key))

        cost_time  = functions.second_to_ms(time.time() - start_time)

        MSG_DAO.add_search_history(user_name, key, cost_time)

        return chatlist, amount

    def do_list_task(self, user_name, offset, limit):
        filter_key = xutils.get_argument("filterKey", "")
        if filter_key != "":
            msg_list, amount = MSG_DAO.list_by_tag(user_name, "task", offset = 0, limit = LIST_LIMIT)
            msg_list = filter_msg_list_by_key(msg_list, filter_key)
            return msg_list, len(msg_list)
        else:
            return MSG_DAO.list_by_tag(user_name, "task", offset, limit)

    def do_list_by_date(self, user_name, date, offset, pagesize):

        filter_key = xutils.get_argument("filterKey", "")
        if filter_key != "":
            msg_list, amount = MSG_DAO.list_by_date(user_name, date, 0, LIST_LIMIT)
            msg_list = filter_msg_list_by_key(msg_list, filter_key)
            return msg_list, len(msg_list)
        else:
            return MSG_DAO.list_by_date(user_name, date, offset, pagesize)

    def do_list_message(self, user_name, tag, offset, pagesize):
        key = xutils.get_argument("key", "")
        date = xutils.get_argument("date", "")
        filter_date = xutils.get_argument("filterDate", "")

        if (tag == "search") or (key != "" and key != None):
            # 搜索
            return self.do_search(user_name, key, offset, pagesize)

        if date != "" and date != None:
            # 日期
            return self.do_list_by_date(user_name, date, offset, pagesize)

        if filter_date != "":
            return self.do_list_by_date(user_name, filter_date, offset, pagesize)

        if tag == "task":
            return self.do_list_task(user_name, offset, pagesize)

        list_func = xutils.lookup_func("message.list_%s" % tag)
        if list_func != None:
            return list_func(user_name, offset, pagesize)
        else:
            return MSG_DAO.list_by_tag(user_name, tag, offset, pagesize)

    @xauth.login_required()
    def GET(self):
        pagesize = xutils.get_argument("pagesize", xconfig.PAGE_SIZE, type=int)
        page   = xutils.get_argument("page", 1, type=int)
        key    = xutils.get_argument("key", "")
        tag    = xutils.get_argument("tag", "task")
        format = xutils.get_argument("format")
        date   = xutils.get_argument("date", "")

        offset = get_offset_from_page(page, pagesize)

        user_name = xauth.get_current_name()

        chatlist, amount = self.do_list_message(user_name, tag, offset, pagesize)

        page_max = get_page_max(amount, pagesize)

        parser = MessageListParser(chatlist)
        parser.parse()
        chatlist = parser.get_message_list()

        if format == "html":
            return self.do_get_html(chatlist, page, page_max, tag)

        return dict(code="success", message = "", 
            data   = chatlist, 
            keywords = parser.get_keywords(),
            amount = amount, 
            page_max = page_max, 
            pagesize = pagesize,
            current_user = xauth.current_name())

def update_message_status(id, status):
    user_name = xauth.current_name()
    data = dbutil.get(id)
    if data and data.user == user_name:
        data.status = status
        data.mtime = xutils.format_datetime()
        
        MSG_DAO.update(data)
        MSG_DAO.refresh_message_stat(user_name)

        xmanager.fire("message.updated", Storage(id=id, user=user_name, status = status, content = data.content))

    return dict(code="success")

def update_message_content(id, user_name, content):
    data = dbutil.get(id)
    if data and data.user == user_name:
        # 先保存历史
        MSG_DAO.add_history(data)

        data.content = content
        data.mtime   = xutils.format_datetime()
        data.version = data.get('version', 0) + 1
        MSG_DAO.update(data)

        xmanager.fire("message.update", dict(id=id, user=user_name, content=content))

        after_message_create_or_update(data)

def create_done_message(old_message):
    old_id = old_message['id']

    new_message = Storage()
    new_message['content'] = ''
    new_message['ref']  = old_id
    new_message['tag'] = 'done'
    new_message['user'] = old_message['user']
    new_message['ctime'] = xutils.format_datetime()

    MSG_DAO.create(**new_message)

def update_message_tag(id, tag):
    user_name = xauth.current_name()
    data = dbutil.get(id)
    if data and data.user == user_name:
        # 修复status数据，全部采用tag
        if 'status' in data:
            del data['status']
        data.tag   = tag
        data.mtime = xutils.format_datetime()
        if tag == "done":
            data.done_time = xutils.format_datetime()
            # 任务完成时除了标记原来任务的完成时间，还要新建一条消息
            create_done_message(data)

        MSG_DAO.update(data)
        MSG_DAO.refresh_message_stat(user_name)
        xmanager.fire("message.updated", Storage(id=id, user=user_name, tag = tag, content = data.content))

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
            return
        if tag in ("task", "cron", "log", "key", "done"):
            return update_message_tag(id, tag)
        else:
            return failure(message = "invalid tag")

class UpdateStatusAjaxHandler:

    @xauth.login_required()
    def POST(self):
        id     = xutils.get_argument("id")
        status = xutils.get_argument("status", type=int)
        return update_message_status(id, status)

class TouchAjaxHandler:

    def do_touch_by_id(self, id):
        msg = MSG_DAO.get_by_id(id)
        if msg is None:
            return failure(message = "message not found, id:%s" % id)
        if msg.user != xauth.current_name():
            return failure(message = "not authorized")
        msg.mtime = xutils.format_datetime()
        MSG_DAO.update(msg)
        return success()

    def do_touch_by_key(self, key):
        user_name = xauth.current_name()
        touch_key_by_content(user_name, "key", key)
        return success()

    @xauth.login_required()
    def POST(self):
        id  = xutils.get_argument("id")
        key = xutils.get_argument("key")

        if id != None and id != "":
            return self.do_touch_by_id(id)
        elif key != "":
            return self.do_touch_by_key(key)
        else:
            return failure(message = "id or key is missing")

class DeleteAjaxHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("id")
        if id == "":
            return
        msg = MSG_DAO.get_by_id(id)
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

rules = [
    CalendarRule(r"(\d+)年(\d+)月(\d+)日"),
]

def get_remote_ip():
    x_forwarded_for = web.ctx.env.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for != None:
        return x_forwarded_for.split(",")[0]
    return web.ctx.env.get("REMOTE_ADDR")

def create_message(user_name, tag, content, ip):
    content = content.strip()
    ctime = xutils.get_argument("date", xutils.format_datetime())
    message = dict(content = content, 
        user   = user_name, 
        tag    = tag,
        ip     = ip,
        mtime  = ctime,
        ctime  = ctime)
    id = MSG_DAO.create(**message)
    message['id'] = id
    MSG_DAO.refresh_message_stat(user_name)

    after_message_create_or_update(MSG_DAO.get_by_id(id))
    
    xmanager.fire('message.add', dict(id=id, user=user_name, content=content, ctime=ctime))

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

def apply_rules(user_name, id, tag, content):
    ctx = Storage(id = id, content = content, user = user_name, type = "")
    for rule in rules:
        rule.match_execute(ctx, content)

class SaveAjaxHandler:

    @xauth.login_required()
    def POST(self):
        id        = xutils.get_argument("id")
        content   = xutils.get_argument("content")
        tag       = xutils.get_argument("tag", DEFAULT_TAG)
        location  = xutils.get_argument("location", "")
        user_name = xauth.get_current_name()
        ip        = get_remote_ip()

        if content == None or content == "":
            return dict(code = "fail", message = "输入内容为空!");

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

class DateAjaxHandler:

    @xauth.login_required()
    def GET(self):
        date      = xutils.get_argument("date")
        page      = xutils.get_argument("page", 1, type = int)
        user_name = xauth.current_name()

        offset = (page - 1) * xconfig.PAGE_SIZE
        limit  = xconfig.PAGE_SIZE

        msg_list, msg_count  = MSG_DAO.list_by_date(user_name, date, offset, limit)

        parser = MessageListParser(msg_list)
        parser.parse()

        page_max = get_page_max(msg_count, xconfig.PAGE_SIZE)

        return xtemplate.render("message/ajax/message_ajax.html", 
            page_max = page_max,
            page = page, 
            page_url = "?date=%s&page=" % date,
            item_list = msg_list)

def filter_key(key):
    if key == None or key == "":
        return ""
    if key[0] == '#':
        return key

    if key[0] == '@':
        return key

    if key[0] == '《' and key[-1] == '》':
        return key
        
    return "#%s#" % key

class MessageListHandler:

    def do_select_key(self):
        user_name = xauth.current_name()
        offset = 0
        pagesize = 1000
        
        msg_list, amount = MSG_DAO.list_by_tag(user_name, "key", offset, pagesize)

        return xtemplate.render("message/page/message_tag_select.html", 
            msg_list = msg_list,
            show_nav = False)

    def do_view_tags(self):
        return xtemplate.render("message/page/message_list_view.html", 
            message_tag = "key",
            search_type = "message",
            show_tag_btn = False,
            show_attachment_btn = False,
            show_system_tag = True,
            message_placeholder = "添加标签/关键字/话题")

    def do_view_by_system_tag(self, tag):
        return xtemplate.render("message/page/message_list_view.html", 
            message_tag = tag,
            search_type = "message",
            show_input_box = False)

    def do_view_task(self):
        filter_key = xutils.get_argument("filterKey", "")
        show_input_box = True
        show_sub_link = True
        show_back_btn = False

        if filter_key != "":
            show_input_box = False
            show_sub_link = False
            show_back_btn = True

        return xtemplate.render("message/page/message_list_view.html", 
            html_title = T("待办任务"),
            message_tag = "task",
            search_type = "message",
            show_system_tag = False,
            show_sub_link = show_sub_link,
            show_input_box = show_input_box,
            show_back_btn = show_back_btn,
            message_placeholder = "添加待办任务")

    def do_view_task_tags(self):
        user_name = xauth.current_name()
        msg_list, amount = MSG_DAO.list_by_tag(user_name, "task", 0, -1)

        tag_list = get_tags_from_message_list(msg_list, "task")

        return xtemplate.render("message/page/message_tag_view.html", 
            message_tag = "task",
            search_type = "message",
            show_back_btn = True,
            tag_list = tag_list,
            html_title = T("待办任务"),
            message_placeholder = "添加待办任务")

    def do_view_month_tags(self):
        user_name = xauth.current_name()
        date = xutils.get_argument("date", "")

        year, month, mday = do_split_date(date)

        msg_list, amount = MSG_DAO.list_by_date(user_name, date, limit = LIST_LIMIT)

        tag_list = get_tags_from_message_list(msg_list, "date", date)

        return xtemplate.render("message/page/message_tag_view.html", 
            year = year,
            month = month,
            message_tag = "calendar",
            search_type = "message",
            show_back_btn = True,
            tag_list = tag_list,
            html_title = T("待办任务"),
            message_placeholder = "添加待办任务")

    def do_view_default(self):
        show_back_btn = False
        key = xutils.get_argument("key", "")
        input_tag = xutils.get_argument("tag", "log")
        default_content = filter_key(key)

        if key != "" or input_tag == "search":
            show_back_btn = True

        return xtemplate.render("message/page/message_list_view.html", 
            tag = input_tag,
            message_tag = input_tag,
            search_type = "message",
            show_system_tag = False,
            show_sub_link = False,
            html_title = T("随手记"),
            default_content = default_content,
            show_back_btn = show_back_btn,
            message_placeholder = "记录发生的事情/产生的想法")

    def do_view_by_date(self, date):
        return xtemplate.render("message/page/message_list_view.html", 
            tag = "date",
            message_tag = "date",
            search_type = "message",
            show_input_box = False,
            show_system_tag = False,
            show_sub_link = False,
            html_title = T("随手记"),
            show_back_btn = True,
            message_placeholder = "记录发生的事情/产生的想法")

    @xauth.login_required()
    def do_get(self, tag = "task"):
        user     = xauth.current_name()
        key      = xutils.get_argument("key", "")
        from_    = xutils.get_argument("from", "")
        show_tab = xutils.get_argument("show_tab", default_value = True, type = bool)
        op       = xutils.get_argument("op", "")
        date     = xutils.get_argument("date", "")

        # 记录日志
        xmanager.add_visit_log(user, "/message?tag=%s" % tag)

        if tag == "month_tags":
            return self.do_view_month_tags()

        if date != "":
            return self.do_view_by_date(date)

        if tag == "key" and op == "select":
            return self.do_select_key()

        if tag == "key":
            return self.do_view_tags()

        if tag in SYSTEM_TAG_TUPLE:
            return self.do_view_by_system_tag(tag)

        if tag == "task":
            return self.do_view_task()

        if tag == "task_tags":
            return self.do_view_task_tags()

        return self.do_view_default()

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
            show_nav = False,
            detail = detail)

class CalendarHandler:

    @xauth.login_required()
    def GET(self):
        user = xauth.current_name()
        date = xutils.get_argument("date")

        year, month, mday = do_split_date(date)

        date = "%s-%02d" % (year, month)

        return xtemplate.render("message/page/message_calendar.html", 
            tag = "calendar",
            year = year,
            month = month,
            date = date,
            html_title = T("随手记"),
            search_type = "message")

class StatAjaxHandler:

    @xauth.login_required()
    def GET(self):
        user = xauth.current_name()
        stat = MSG_DAO.get_message_stat(user)
        format_message_stat(stat)
        return stat

class DairyHandler:

    @xauth.login_required()
    def GET(self):
        return xtemplate.render("message/page/dairy.html")

class MessageHandler(MessageListHandler):
    pass

class MessageLogHandler(MessageHandler):

    def GET(self):
        return self.do_get("log")

class TodoHandler(MessageHandler):

    @xauth.login_required()
    def do_get(self, tag = "todo", title = "待办任务", show_input_box = True):
        user_name = xauth.current_name()
        message_stat = MSG_DAO.get_message_stat(user_name)
        xmanager.add_visit_log(user_name, "/message/todo")
        
        return xtemplate.render("message/page/message_todo.html", 
            search_type = "task",
            tag = tag,
            title = T(title),
            show_input_box = show_input_box,
            message_stat = message_stat)

    def GET(self):
        return self.do_get("todo")

class TodoDoneHandler(TodoHandler):

    def GET(self):
        return self.do_get("done", "已完成任务", show_input_box = False)

class TodoCanceledHandler(TodoHandler):

    def GET(self):
        return self.do_get("canceled", "已取消任务", show_input_box = False)


class MessageListByDayHandler():

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
        date = xutils.get_argument("date")

        year, month, day = do_split_date(date)

        item_list, amount = MSG_DAO.list_by_date(user_name, date, limit = LIST_LIMIT)
        message_list = []

        for item in item_list:
            date = dateutil.format_date(item.ctime)
            has_found = False
            for key, value, wday in message_list:
                if key == date:
                    value.append(item)
                    has_found = True
            if not has_found:
                message_list.append((date, [item], dateutil.format_wday(date)))

        message_list.sort(key = lambda x: x[0], reverse = True)

        return xtemplate.render("message/page/message_list_by_day.html", 
            year = year,
            month = month,
            message_list = message_list,
            show_back_btn = True,
            tag = "date")

class MessageRefreshHandler:

    @xauth.login_required("admin")
    def GET(self):
        refresh_key_amount()
        return "success"

xutils.register_func("message.process_message", process_message)
xutils.register_func("message.get_current_message_stat", get_current_message_stat)
xutils.register_func("url:/message/log", MessageLogHandler)

xurls=(
    r"/message", MessageHandler,
    r"/message/calendar", CalendarHandler,
    r"/message/dairy", DairyHandler,
    r"/message/todo", TodoHandler,
    r"/message/log", MessageLogHandler,
    r"/message/done", TodoDoneHandler,
    r"/message/canceled", TodoCanceledHandler,
    r"/message/edit", MessageEditHandler,
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
)
