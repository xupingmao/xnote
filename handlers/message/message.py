# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/29
# @since 2017/08/04
# @modified 2019/12/15 00:12:04

"""短消息"""
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
from xutils import BaseRule, Storage, cacheutil, dbutil, textutil, functions, u, SearchResult
from xtemplate import T

MSG_DAO       = xutils.DAO("message")
DEFAULT_TAG   = "log"
TAG_TEXT_DICT = dict(
    done = "完成",
    cron = "定期",
    task = "任务",
    log  = "记事",
    key  = "话题"
)

def success():
    return dict(success = True, code = "success")

def failure(message, code = "fail"):
    return dict(success = False, code = code, message = message)

def build_search_html(content):
    fmt = u'搜索 <a href="/message?category=message&key=%s">%s</a>'
    return fmt % (xutils.encode_uri_component(content), xutils.html_escape(content))

def build_done_html(message):
    task = None
    done_time = message.done_time

    if message.ref != None:
        task = MSG_DAO.get_by_id(message.ref)

    if task != None:
        message.html = u("完成任务:<br>&gt;&nbsp;") + xutils.mark_text(task.content)
    elif done_time is None:
        done_time = message.mtime
        message.html += u("<br>------<br>完成于 %s") % done_time

def process_message(message):
    if message.status == 0 or message.status == 50:
        # 兼容历史数据
        message.tag = "task"
    if message.status == 100:
        message.tag = "done"

    message.tag_text = TAG_TEXT_DICT.get(message.tag, message.tag)

    if message.content is None:
        message.content = ""
        return message

    if message.tag == "key" or message.tag == "search":
        message.html = build_search_html(message.content)
    else:
        message.html = xutils.mark_text(message.content)

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
def on_search_scripts(ctx):
    key = ctx.key
    messages, count = MSG_DAO.search(ctx.user_name, key, 0, 3)
    for message in messages:
        item = SearchResult()
        process_message(message)
        item.name = message.ctime
        item.html = message.html
        ctx.tools.append(item)
        # print(message)
    if count > 3:
        more = SearchResult()
        more.name = "查看更多备忘"
        more.url  = "/message?key=" + ctx.key
        ctx.tools.append(more)

class SearchContext:

    def __init__(self, key):
        self.key = key

class ListAjaxHandler:

    def GET(self):
        pagesize = xutils.get_argument("pagesize", xconfig.PAGE_SIZE, type=int)
        page   = xutils.get_argument("page", 1, type=int)
        key    = xutils.get_argument("key")
        tag    = xutils.get_argument("tag", "task")
        offset = (page-1) * pagesize
        user_name = xauth.get_current_name()

        if key != "" and key != None:
            # 搜索
            start_time = time.time()
            chatlist, amount = MSG_DAO.search(user_name, key, offset, pagesize)

            xmanager.fire("message.search", SearchContext(key))

            cost_time  = functions.second_to_ms(time.time() - start_time)
            MSG_DAO.add_search_history(user_name, key, cost_time)
        elif tag == "file":
            # 文件
            chatlist, amount = MSG_DAO.list_file(user_name, offset, pagesize)
        elif tag == "link":
            # 链接
            chatlist, amount = MSG_DAO.list_link(user_name, offset, pagesize)
        else:
            if tag == "task" or tag == "key":
                pagesize = 1000
            chatlist, amount = MSG_DAO.list_by_tag(user_name, tag, offset, pagesize)
            
        page_max = math.ceil(amount / pagesize)
        chatlist = list(map(process_message, chatlist))

        return dict(code="success", message = "", 
            data   = chatlist, 
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

def add_done_message(old_message):
    old_id = old_message['id']

    new_message = old_message.copy()
    new_message['id'] = None
    new_message['content'] = ''
    new_message['ref']  = old_id
    new_message['type'] = 'done'

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
            add_done_message(data)

        MSG_DAO.update(data)
        MSG_DAO.refresh_message_stat(user_name)
        xmanager.fire("message.updated", Storage(id=id, user=user_name, tag = tag, content = data.content))

    return dict(code="success")

class FinishMessageHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("id")
        if id == "":
            return
        return update_message_tag(id, "done")

class OpenMessageHandler:

    def POST(self):
        id = xutils.get_argument("id")
        if id == "":
            return
        return update_message_tag(id, "task")

class UpdateTagHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("id")
        tag = xutils.get_argument("tag")
        if id == "":
            return
        if tag in ("task", "cron", "log", "key"):
            return update_message_tag(id, tag)
        else:
            return failure(message = "invalid tag")

class UpdateStatusHandler:

    @xauth.login_required()
    def POST(self):
        id     = xutils.get_argument("id")
        status = xutils.get_argument("status", type=int)
        return update_message_status(id, status)

class TouchHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("id")
        msg = MSG_DAO.get_by_id(id)
        if msg is None:
            return failure(message = "message not found, id:%s" % id)
        if msg.user != xauth.current_name():
            return failure(message = "not authorized")
        msg.mtime = xutils.format_datetime()
        MSG_DAO.update(msg)
        return success()

class DeleteHandler:

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

def apply_rules(user_name, id, tag, content):
    ctx = Storage(id = id, content = content, user = user_name, type = "")
    for rule in rules:
        rule.match_execute(ctx, content)

class SaveHandler:

    @xauth.login_required()
    def POST(self):
        id        = xutils.get_argument("id")
        content   = xutils.get_argument("content")
        tag       = xutils.get_argument("tag", DEFAULT_TAG)
        location  = xutils.get_argument("location", "")
        user_name = xauth.get_current_name()
        ip        = get_remote_ip()

        # 对消息进行语义分析处理，后期优化把所有规则统一管理起来
        apply_rules(user_name, id, tag, content)

        if id == "" or id is None:
            item = check_content_for_update(user_name, tag, content)
            if item != None:
                item.mtime = xutils.format_datetime()
                MSG_DAO.update(item)
                message = item
            else:
                message = create_message(user_name, tag, content, ip)            
            return dict(code="success", data=message)
        else:
            update_message_content(id, user_name, content)
        return dict(code="success", data=dict(id=id))

class DateHandler:

    @xauth.login_required()
    def GET(self):
        date      = xutils.get_argument("date")
        user_name = xauth.current_name()
        if date != None:
            msg_list = MSG_DAO.list_by_date(user_name, date)
        else:
            msg_list = []
        return dict(code="success", data = msg_list)

class MessageHandler:

    @xauth.login_required()
    def GET(self):
        user     = xauth.current_name()
        key      = xutils.get_argument("key", "")
        from_    = xutils.get_argument("from")
        show_tab = (xutils.get_argument("show_tab") != "false")

        if key != None and key != "":
            if key[0] == '#':
                # 精确搜索
                default_content = key
            else:
                default_content = "#%s# " % key
        else:
            default_content = ""

        stat = MSG_DAO.get_message_stat(user)
        stat = format_message_stat(stat)

        return xtemplate.render("message/message.html", 
            show_aside         = False,
            show_tab           = show_tab,
            category           = "message",
            search_action      = "/message", 
            html_title         = T("待办"),
            search_placeholder = T("搜索待办事项"),
            default_content    = default_content,
            message_stat       = stat,
            key                = key,
            from_              = from_)


class CalendarHandler:

    def GET(self):
        user = xauth.current_name()
        stat = MSG_DAO.get_message_stat(user)
        stat = format_message_stat(stat)

        return xtemplate.render("message/calendar.html", 
            show_aside = False,
            message_stat = stat,
            search_action      = "/message", 
            search_placeholder = T("搜索待办事项"))

class StatHandler:

    @xauth.login_required()
    def GET(self):
        user = xauth.current_name()
        stat = MSG_DAO.get_message_stat(user)
        format_message_stat(stat)
        return stat
xurls=(
    r"/message", MessageHandler,
    r"/message/list", ListAjaxHandler,
    r"/message/calendar", CalendarHandler,
    r"/message/stat", StatHandler,
    r"/message/date", DateHandler,
    
    r"/message/save", SaveHandler,
    r"/message/status", UpdateStatusHandler,
    r"/message/delete", DeleteHandler,
    r"/message/update", SaveHandler,
    r"/message/open", OpenMessageHandler,
    r"/message/finish", FinishMessageHandler,
    r"/message/touch", TouchHandler,
    r"/message/tag", UpdateTagHandler
)
