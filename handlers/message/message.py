# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/29
# @since 2017/08/04
# @modified 2019/11/23 16:23:00

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

def process_message(message):
    if message.content is None:
        message.content = ""
        return message
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

class ListHandler:

    def GET(self):
        pagesize = xutils.get_argument("pagesize", xconfig.PAGE_SIZE, type=int)
        page   = xutils.get_argument("page", 1, type=int)
        status = xutils.get_argument("status")
        key    = xutils.get_argument("key")
        tag    = xutils.get_argument("tag")
        offset = (page-1) * pagesize
        user_name = xauth.get_current_name()
        # 未完成任务的分页
        undone_pagesize = 1000
        status_num = None

        kw = "1=1"
        if status == "created":
            status_num = 0
            kw = "status = 0"
            pagesize = undone_pagesize
        if status == "done":
            status_num = 100
            kw = "status = 100"
        if status == "suspended":
            status_num = 50
            kw = "status = 50"
            pagesize = undone_pagesize

        if tag == "file":
            chatlist, amount = xutils.call("message.list_file", user_name, offset, pagesize)
        elif key != "" and key != None:
            chatlist, amount = xutils.call("message.search", user_name, key, offset, pagesize)
        else:
            chatlist, amount = xutils.call("message.list", user_name, status_num, offset, pagesize)
            
        chatlist.reverse()
        page_max = math.ceil(amount / pagesize)
        chatlist = list(map(process_message, chatlist))
        return dict(code="success", message="", 
            pagesize = pagesize,
            data=chatlist, 
            amount=amount, 
            page_max=page_max, 
            current_user=xauth.get_current_name())

def update_message_status(id, status):
    if xconfig.DB_ENGINE == "sqlite":
        db = xtables.get_message_table()
        msg = db.select_first(where=dict(id=id))
        if msg is None:
            return dict(code="fail", message="data not exists")
        if msg.user != xauth.get_current_name():
            return dict(code="fail", message="no permission")
        db.update(status=status, mtime=xutils.format_datetime(), where=dict(id=id))
        xmanager.fire("message.updated", Storage(id=id, status=status, user = msg.user, content=msg.content))
    else:
        user_name = xauth.current_name()
        data = dbutil.get(id)
        if data and data.user == user_name:
            data.status = status
            data.mtime = xutils.format_datetime()
            dbutil.put(id, data)
            xmanager.fire("message.updated", Storage(id=id, user=user_name, status = status, content = data.content))

    return dict(code="success")

def update_message_content(id, user_name, content):
    if xconfig.DB_ENGINE == "sqlite":
        db = xtables.get_message_table()
        db.update(content = content,
            mtime = xutils.format_datetime(), 
            where = dict(id=id, user=user_name))
        xmanager.fire("message.update", dict(id=id, user=user_name, content=content))
    else:
        data = dbutil.get(id)
        if data and data.user == user_name:
            data.content = content
            data.mtime = xutils.format_datetime()
            dbutil.put(id, data)
            xmanager.fire("message.update", dict(id=id, user=user_name, content=content))

class FinishMessage:

    def POST(self):
        id = xutils.get_argument("id")
        if id == "":
            return
        return update_message_status(id, 100)

class OpenMessage:

    def POST(self):
        id = xutils.get_argument("id")
        if id == "":
            return
        return update_message_status(id, 0)
        
class UpdateStatusHandler:

    def POST(self):
        id     = xutils.get_argument("id")
        status = xutils.get_argument("status", type=int)
        return update_message_status(id, status)

class RemoveHandler:

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

        xutils.call("message.delete", id)
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
        status    = xutils.get_argument("status")
        location  = xutils.get_argument("location", "")
        user_name = xauth.get_current_name()
        # 对消息进行语义分析处理，后期优化把所有规则统一管理起来
        ctx = Storage(id = id, content = content, user = user_name, type = "")
        for rule in rules:
            rule.match_execute(ctx, content)

        ip = get_remote_ip()

        if id == "" or id is None:
            ctime = xutils.get_argument("date", xutils.format_datetime())
            inserted_id = xutils.call("message.create", content = content, 
                user   = user_name, 
                status = get_status_by_code(status),
                ip     = ip,
                mtime  = ctime,
                ctime  = ctime)
            id = inserted_id
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
        from .dao import count_message
        return xtemplate.render("message/message.html", 
            show_aside         = False,
            category           = "message",
            search_action      = "/message", 
            html_title         = T("待办"),
            search_placeholder = T("搜索目标"),
            count_message      = count_message,
            key                = xutils.get_argument("key", ""))


class CalendarHandler:

    def GET(self):
        from .dao import count_message
        return xtemplate.render("message/calendar.html", 
            show_aside = False,
            count_message = count_message)

xurls=(
    r"/message", MessageHandler,
    r"/message/add", SaveHandler,
    r"/message/status", UpdateStatusHandler,
    r"/message/list", ListHandler,
    r"/message/remove", RemoveHandler,
    r"/message/update", SaveHandler,
    r"/message/open", OpenMessage,
    r"/message/finish", FinishMessage,
    r"/message/date", DateHandler,
    r"/message/calendar", CalendarHandler
)
