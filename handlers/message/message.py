# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/29
# @since 2017/08/04
# @modified 2021/05/23 14:23:18

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
        message.html = build_search_html(message.content)
    else:
        html, keywords = mark_text(message.content)
        message.html = html
        message.keywords = keywords

    if message.tag == "done":
        build_done_html(message)
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
        show_todo_check = False
        show_edit_btn   = True
        show_to_log_btn = False

        if tag == "todo":
            show_todo_check = True
            show_to_log_btn = True

        if tag == "done":
            show_to_log_btn = True

        if tag == "key":
            show_edit_btn = False

        return xtemplate.render("message/ajax/message_ajax.html", 
            show_todo_check = show_todo_check,
            show_edit_btn = show_edit_btn,
            show_to_log_btn = show_to_log_btn,
            page = page,
            page_max = page_max,
            item_list = chatlist)

    def do_search(self, user_name, key, offset, pagesize):
        # 搜索
        start_time = time.time()
        chatlist, amount = MSG_DAO.search(user_name, key, offset, pagesize)

        # 搜索扩展
        xmanager.fire("message.search", SearchContext(key))

        # 自动置顶
        touch_key_by_content(user_name, "key", key)

        cost_time  = functions.second_to_ms(time.time() - start_time)

        MSG_DAO.add_search_history(user_name, key, cost_time)

        return chatlist, amount


    @xauth.login_required()
    def GET(self):
        pagesize = xutils.get_argument("pagesize", xconfig.PAGE_SIZE, type=int)
        page   = xutils.get_argument("page", 1, type=int)
        key    = xutils.get_argument("key")
        tag    = xutils.get_argument("tag", "task")
        format = xutils.get_argument("format")
        offset = (page-1) * pagesize
        user_name = xauth.get_current_name()

        if key != "" and key != None:
            # 搜索
            chatlist, amount = self.do_search(user_name, key, offset, pagesize)
        elif tag in ("task", "todo", "key"):
            # 任务
            pagesize = 1000
            chatlist, amount = MSG_DAO.list_by_tag(user_name, tag, offset, pagesize)
        else:
            list_func = xutils.lookup_func("message.list_%s" % tag)
            if list_func != None:
                chatlist, amount = list_func(user_name, offset, pagesize)
            else:
                chatlist, amount = MSG_DAO.list_by_tag(user_name, tag, offset, pagesize)

        page_max = math.ceil(amount / pagesize)

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
        user_name = xauth.current_name()
        msg_list = MSG_DAO.list_by_date(user_name, date)

        parser = MessageListParser(msg_list)
        parser.parse()

        # return dict(code="success", data = msg_list)
        return xtemplate.render("message/ajax/message_ajax.html", 
            page = 0, item_list = msg_list)

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

class MessageHandler:

    @xauth.login_required()
    def do_get(self, tag = "task"):
        user     = xauth.current_name()
        key      = xutils.get_argument("key", "")
        from_    = xutils.get_argument("from")
        show_tab = xutils.get_argument("show_tab", default_value = True, type = bool)

        default_content = filter_key(key)

        stat = MSG_DAO.get_message_stat(user)
        stat = format_message_stat(stat)

        xmanager.add_visit_log(user, "/message?tag=%s" % tag)

        return xtemplate.render("message/page/message.html", 
            show_tab           = show_tab,
            category           = "message",
            search_type        = "message",
            html_title         = T("随手记"),
            default_content    = default_content,
            message_stat       = stat,
            tag                = tag,
            search_tag         = tag,
            key                = key,
            from_              = from_)

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

    def GET(self):
        user = xauth.current_name()
        stat = MSG_DAO.get_message_stat(user)
        stat = format_message_stat(stat)

        return xtemplate.render("message/page/calendar.html", 
            tag = "calendar",
            show_aside = False,
            message_stat = stat,
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

class MessageLogHandler(MessageHandler):

    def GET(self):
        return self.do_get("log")

class TodoHandler(MessageHandler):

    @xauth.login_required()
    def do_get(self, tag = "todo", title = "待办任务", show_input_box = True):
        user_name = xauth.current_name()
        message_stat = MSG_DAO.get_message_stat(user_name)
        xmanager.add_visit_log(user_name, "/message/todo")
        
        return xtemplate.render("message/page/todo.html", 
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

    def do_split_date(self, date):
        parts = date.split("-")
        if len(parts) >= 2:
            year = int(parts[0])
            month = int(parts[1])
        elif len(parts) == 1:
            year = int(parts[0])
            month = dateutil.get_current_month()
        return year, month

    @xauth.login_required()
    def GET(self):
        user_name = xauth.current_name()
        date = xutils.get_argument("date")

        year, month = self.do_split_date(date)

        item_list = MSG_DAO.list_by_date(user_name, date, limit = LIST_LIMIT)
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
            tag = "date")

class MessageDetailHandler:

    @xauth.login_required()
    def GET(self):
        date = xutils.get_argument("date")
        return xtemplate.render("message/page/message_detail.html", tag = "date", date = date)

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
    r"/message/detail", MessageDetailHandler,

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
