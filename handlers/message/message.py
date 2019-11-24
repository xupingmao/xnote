# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/29
# @since 2017/08/04
# @modified 2019/11/25 01:23:31

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
from xutils import BaseRule, Storage, cacheutil, dbutil, textutil
from xtemplate import T

MSG_DAO = xutils.DAO("message")
DEFAULT_TAG = "log"

def build_search_html(content):
    return '搜索 <a href="/message?category=message&key=%s">%s</a>' % (xutils.encode_uri_component(content), xutils.html_escape(content))

def process_message(message):
    if message.status == 0 or message.status == 50:
        # 兼容历史数据
        message.tag = "task"
    if message.status == 100:
        message.tag = "done"

    if message.content is None:
        message.content = ""
        return message
    if message.tag == "search":
        message.html = build_search_html(message.content)
    else:
        message.html = xutils.mark_text(message.content)
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
    return stat

class ListHandler:

    def GET(self):
        pagesize = xutils.get_argument("pagesize", xconfig.PAGE_SIZE, type=int)
        page   = xutils.get_argument("page", 1, type=int)
        key    = xutils.get_argument("key")
        tag    = xutils.get_argument("tag", "task")
        offset = (page-1) * pagesize
        user_name = xauth.get_current_name()

        if tag == "task":
            pagesize = 1000

        if key != "" and key != None:
            # 搜索
            start_time = time.time()
            chatlist, amount = MSG_DAO.search(user_name, key, offset, pagesize)
            cost_time  = time.time() - start_time
            MSG_DAO.add_search_history(user_name, key, cost_time)
        elif tag == "file":
            # 文件
            chatlist, amount = MSG_DAO.list_file(user_name, offset, pagesize)
        elif tag == "link":
            # 链接
            chatlist, amount = MSG_DAO.list_link(user_name, offset, pagesize)
        else:
            # 所有的
            chatlist, amount = MSG_DAO.list_by_tag(user_name, tag, offset, pagesize)
            
        page_max = math.ceil(amount / pagesize)
        chatlist = list(map(process_message, chatlist))

        return dict(code="success", message="", 
            pagesize = pagesize,
            data = chatlist, 
            amount = amount, 
            page_max = page_max, 
            current_user = xauth.get_current_name())

def update_message_status(id, status):
    user_name = xauth.current_name()
    data = dbutil.get(id)
    if data and data.user == user_name:
        data.status = status
        data.mtime = xutils.format_datetime()
        dbutil.put(id, data)
        MSG_DAO.refresh_message_stat(user_name)
        xmanager.fire("message.updated", Storage(id=id, user=user_name, status = status, content = data.content))

    return dict(code="success")

def update_message_content(id, user_name, content):
    data = dbutil.get(id)
    if data and data.user == user_name:
        data.content = content
        data.mtime = xutils.format_datetime()
        dbutil.put(id, data)
        xmanager.fire("message.update", dict(id=id, user=user_name, content=content))

def update_message_tag(id, tag):
    user_name = xauth.current_name()
    data = dbutil.get(id)
    if data and data.user == user_name:
        # 修复status数据，全部采用tag
        if 'status' in data:
            del data['status']
        data.tag   = tag
        data.mtime = xutils.format_datetime()
        dbutil.put(id, data)
        MSG_DAO.refresh_message_stat(user_name)
        xmanager.fire("message.updated", Storage(id=id, user=user_name, tag = tag, content = data.content))

    return dict(code="success")

class FinishMessage:

    def POST(self):
        id = xutils.get_argument("id")
        if id == "":
            return
        return update_message_tag(id, "done")

class OpenMessage:

    def POST(self):
        id = xutils.get_argument("id")
        if id == "":
            return
        return update_message_tag(id, "task")
        
class UpdateStatusHandler:

    def POST(self):
        id     = xutils.get_argument("id")
        status = xutils.get_argument("status", type=int)
        return update_message_status(id, status)

class DeleteHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("id")
        if id == "":
            return
        msg = xutils.call("message.find_by_id", id)
        if msg is None:
            return dict(code="fail", message="data not exists")
        
        if msg.user != xauth.current_name():
            return dict(code="fail", message="no permission")

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

class SaveHandler:

    @xauth.login_required()
    def POST(self):
        id        = xutils.get_argument("id")
        content   = xutils.get_argument("content")
        tag       = xutils.get_argument("tag", DEFAULT_TAG)
        location  = xutils.get_argument("location", "")
        user_name = xauth.get_current_name()

        # 对消息进行语义分析处理，后期优化把所有规则统一管理起来
        ctx = Storage(id = id, content = content, user = user_name, type = "")
        for rule in rules:
            rule.match_execute(ctx, content)

        ip = get_remote_ip()

        if id == "" or id is None:
            ctime = xutils.get_argument("date", xutils.format_datetime())
            inserted_id = MSG_DAO.create(content = content, 
                user   = user_name, 
                tag    = tag,
                ip     = ip,
                mtime  = ctime,
                ctime  = ctime)
            id = inserted_id
            MSG_DAO.refresh_message_stat(user_name)
            
            xmanager.fire('message.add', dict(id=id, user=user_name, content=content, ctime=ctime))
            return dict(code="success", data=dict(id=inserted_id, content=content, ctime=ctime))
        else:
            update_message_content(id, user_name, content)
        return dict(code="success", data=dict(id=id))

class DateHandler:

    @xauth.login_required()
    def GET(self):
        date = xutils.get_argument("date")
        db = xtables.get_message_table()
        data = db.select(where="ctime LIKE $date AND user=$user LIMIT 200", 
            vars = dict(date = date + '%', user=xauth.get_current_name()))
        return dict(code="success", data = list(data))

class MessageHandler:

    @xauth.login_required()
    def GET(self):
        user = xauth.current_name()
        key  = xutils.get_argument("key", "")
        if key != None and key != "":
            default_content = "#%s# " % key
        else:
            default_content = ""

        stat = MSG_DAO.get_message_stat(user)
        stat = format_message_stat(stat)

        return xtemplate.render("message/message.html", 
            show_aside         = False,
            category           = "message",
            search_action      = "/message", 
            html_title         = T("待办"),
            search_placeholder = T("搜索待办"),
            default_content    = default_content,
            message_stat       = stat,
            key                = key)


class CalendarHandler:

    def GET(self):
        from .dao import count_message
        user = xauth.current_name()
        return xtemplate.render("message/calendar.html", 
            show_aside = False,
            message_stat = MSG_DAO.get_message_stat(user),
            count_message = count_message)

class StatHandler:

    @xauth.login_required()
    def GET(self):
        user = xauth.current_name()
        stat = MSG_DAO.get_message_stat(user)
        format_message_stat(stat)
        return stat
xurls=(
    r"/message", MessageHandler,
    r"/message/save", SaveHandler,
    r"/message/status", UpdateStatusHandler,
    r"/message/list", ListHandler,
    r"/message/delete", DeleteHandler,
    r"/message/update", SaveHandler,
    r"/message/open", OpenMessage,
    r"/message/finish", FinishMessage,
    r"/message/date", DateHandler,
    r"/message/calendar", CalendarHandler,
    r"/message/stat", StatHandler
)
