# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/29
# @since 2017/08/04
# @modified 2019/04/27 23:04:12

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
    message.html = xutils.mark_text(message.content)
    return message

def fuzzy_item(item):
    item = item.replace("'", "''")
    return "'%%%s%%'" % item

def db_call(name, *args):
    if xconfig.DB_ENGINE == "sqlite":
        return globals()["rdb_" + name](*args)
    else:
        return globals()["kv_" + name](*args)

@xutils.timeit(name = "Rdb.Message.Count", logfile = True)
def rdb_count_message(user, status):
    count = xtables.get_message_table().count(where="user=$user AND status=$status",
        vars = dict(user = user, status = status))
    return count

@xutils.timeit(name = "Kv.Message.Count", logfile = True)
def kv_count_message(user, status):
    def filter_func(k, v):
        return v.status == status
    return dbutil.prefix_count("message:%s" % user, filter_func = filter_func)

@xutils.cache(prefix="message.count.status", expire=60)
def count_message(user, status):
    return db_call("count_message", user, status)


def create_message(**kw):
    if xconfig.DB_ENGINE == "sqlite":
        db = xtables.get_message_table()
        return db.insert(**kw)
    else:
        key      = "message:%s:%s" % (kw['user'], dbutil.timeseq())
        kw['id'] = key
        dbutil.put(key, kw)
        return key

def get_status_by_code(code):
    if code == "created":
        return 0
    if code == "suspended":
        return 50
    if code == "done":
        return 100
    return 0


def rdb_list_message_page(user, status, offset, limit):
    db = xtables.get_message_table()
    kw = dict(user=user, status=status)
    chatlist = list(db.select(where=kw, order="ctime DESC", limit=limit, offset=offset))
    amount = db.count(where=kw)
    return chatlist, amount

@xutils.timeit(name = "kv.message.list", logfile = True, logargs = True)
def kv_list_message_page(user, status, offset, limit):
    def filter_func(key, value):
        if status is None:
            return value.user == user
        return value.user == user and value.status == status
    chatlist = dbutil.prefix_list("message:%s" % user, filter_func, offset, limit, reverse = True)
    amount   = dbutil.prefix_count("message:%s" % user, filter_func)
    return chatlist, amount

def list_message_page(*args):
    return db_call("list_message_page", *args)

def rdb_search_message(user_name, key, offset, limit):
    db   = xtables.get_message_table()
    vars = dict(user= user_name)
    kw = "user = $user"
    start_time = time.time()
    for item in key.split(" "):
        if item == "":
            continue
        kw += " AND content LIKE " + fuzzy_item(item)
    # when find numbers, the sql printed is not correct
    # eg. LIKE '%1%' will be LIKE '%'
    chatlist = list(db.select(where=kw, vars=vars, order="ctime DESC", limit=limit, offset=offset))
    end_time = time.time()
    cost_time = int((end_time-start_time)*1000)
    xutils.trace("MessageSearch", key, cost_time)
    if xconfig.search_history is not None:
        xconfig.search_history.add(key, cost_time)

    amount = db.count(where=kw, vars=vars)
    return chatlist, amount

def kv_search_message(user_name, key, offset, limit):
    words = []
    for item in key.split(" "):
        if item == "":
            continue
        words.append(item)

    def search_func(key, value):
        return value.user == user_name and textutil.contains_all(value.content, words)

    chatlist = dbutil.prefix_list("message:%s" % user_name, search_func, offset, limit, reverse = True)
    amount   = dbutil.prefix_count("message:%s" % user_name, search_func)
    return chatlist, amount

def search_message(*args):
    return db_call("search_message", *args)

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
        if key != "" and key != None:
            chatlist, amount = search_message(user_name, key, offset, pagesize)
        else:
            chatlist, amount = list_message_page(user_name, status_num, offset, pagesize)
            
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

@xmanager.listen(["message.updated", "message.add", "message.remove"])
def expire_message_cache(ctx):
    cacheutil.prefix_del("message.count")

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
        db = xtables.get_message_table()
        # 对消息进行语义分析处理，后期优化把所有规则统一管理起来
        ctx = Storage(id = id, content = content, user = user_name, type = "")
        for rule in rules:
            rule.match_execute(ctx, content)

        ip = get_remote_ip()

        if id == "" or id is None:
            ctime = xutils.get_argument("date", xutils.format_datetime())
            inserted_id = create_message(content = content, 
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
        return xtemplate.render("message/message.html", 
            show_aside         = False,
            category           = "message",
            search_action      = "/message", 
            html_title         = T("提醒"),
            search_placeholder = T("搜索提醒"),
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

xutils.register_func("message.count", count_message)
