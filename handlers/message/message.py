# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/29
# @since 2017/08/04
# @modified 2019/01/13 16:16:09

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
from xutils import BaseRule, Storage, cacheutil

def process_message(message):
    message.html = xutils.mark_text(message.content)
    return message

def fuzzy_item(item):
    item = item.replace("'", "''")
    return "'%%%s%%'" % item

@xutils.cache(prefix="message.count.status", expire=60)
def count_message(user, status):
    count = xtables.get_message_table().count(where="user=$user AND status=$status",
        vars = dict(user = user, status = status))
    return count

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
        offset = (page-1) * pagesize
        db = xtables.get_message_table()
        user_name = xauth.get_current_name()
        # 未完成任务的分页
        undone_pagesize = 1000

        kw = "1=1"
        if status == "created":
            kw = "status = 0"
            pagesize = undone_pagesize
        if status == "done":
            kw = "status = 100"
        if status == "suspended":
            kw = "status = 50"
            pagesize = undone_pagesize
        kw += " AND user = $user"
        vars = dict(user=xauth.get_current_name())
        if key != "" and key != None:
            start_time = time.time()
            for item in key.split(" "):
                if item == "":
                    continue
                kw += " AND content LIKE " + fuzzy_item(item)
            # when find numbers, the sql printed is not correct
            # eg. LIKE '%1%' will be LIKE '%'
            # print(kw)
            chatlist = list(db.select(where=kw, vars=vars, order="ctime DESC", limit=pagesize, offset=offset))
            end_time = time.time()
            cost_time = int((end_time-start_time)*1000)
            xutils.trace("MessageSearch", key, cost_time)
            if xconfig.search_history is not None:
                xconfig.search_history.add(key, cost_time)
        else:
            chatlist = list(db.select(where=kw, vars=vars, order="ctime DESC", limit=pagesize, offset=offset))
        chatlist.reverse()
        amount = db.count(where=kw, vars=vars)
        page_max = math.ceil(amount / pagesize)
        chatlist = list(map(process_message, chatlist))
        return dict(code="success", message="", 
            pagesize = pagesize,
            data=chatlist, amount=amount, 
            page_max=page_max, current_user=xauth.get_current_name())

def update_message(id, status):
    db = xtables.get_message_table()
    msg = db.select_first(where=dict(id=id))
    if msg is None:
        return dict(code="fail", message="data not exists")
    if msg.user != xauth.get_current_name():
        return dict(code="fail", message="no permission")
    db.update(status=status, mtime=xutils.format_datetime(), where=dict(id=id))
    xmanager.fire("message.update", Storage(id=id, status=status, user = msg.user, content=msg.content))
    return dict(code="success")

class FinishMessage:

    def POST(self):
        id = xutils.get_argument("id")
        if id == "":
            return
        return update_message(id, 100)

class OpenMessage:

    def POST(self):
        id = xutils.get_argument("id")
        if id == "":
            return
        return update_message(id, 0)
        
class UpdateStatusHandler:

    def POST(self):
        id     = xutils.get_argument("id")
        status = xutils.get_argument("status", type=int)
        return update_message(id, status)

class RemoveHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("id")
        if id == "":
            return
        db = xtables.get_message_table()
        msg = db.select_first(where=dict(id=id))
        if msg is None:
            return dict(code="fail", message="data not exists")
        
        if msg.user != xauth.get_current_name():
            return dict(code="fail", message="no permission")
        db.delete(where=dict(id=id))
        xmanager.fire("message.remove", Storage(id=id))
        return dict(code="success")


class CalendarRule(BaseRule):

    def execute(self, ctx, date, month, day):
        print(date, month, day)
        ctx.type = "calendar"

@xmanager.listen(["message.update", "message.add", "message.remove"])
def expire_message_cache(ctx):
    cacheutil.prefix_del("message.count")

rules = [
    CalendarRule(r"(\d+)年(\d+)月(\d+)日"),
]

class SaveHandler:

    @xauth.login_required()
    def POST(self):
        id        = xutils.get_argument("id")
        content   = xutils.get_argument("content")
        status    = xutils.get_argument("status")
        user_name = xauth.get_current_name()
        db = xtables.get_message_table()
        # 对消息进行语义分析处理，后期优化把所有规则统一管理起来
        ctx = Storage(id = id, content = content, user = user_name, type = "")
        for rule in rules:
            rule.match_execute(ctx, content)

        if id == "" or id is None:
            ctime = xutils.get_argument("date", xutils.format_datetime())
            inserted_id = db.insert(content = content, 
                user   = user_name, 
                status = get_status_by_code(status),
                mtime  = ctime,
                ctime  = ctime)
            id = inserted_id
            xmanager.fire('message.add', dict(id=id, user=user_name, content=content, ctime=ctime))
            return dict(code="success", data=dict(id=inserted_id, content=content, ctime=ctime))
        else:
            db.update(content = content,
                mtime = xutils.format_datetime(), 
                where = dict(id=id, user=user_name))
            xmanager.fire("message.update", dict(id=id, user=user_name, content=content))
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
        return xtemplate.render("message/message.html", 
            show_aside         = False,
            category           = "message",
            search_action      = "/message", 
            html_title         = "提醒",
            search_placeholder = "搜索提醒信息",
            count_message      = count_message,
            key                = xutils.get_argument("key", ""))


class CalendarHandler:

    def GET(self):
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

