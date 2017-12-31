# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/29
# 

"""短消息"""
import math
import xutils
import xtables
import xauth
import xconfig
from xutils import BaseRule, Storage

class ListHandler:

    def GET(self):
        pagesize = xutils.get_argument("pagesize", xconfig.PAGE_SIZE, type=int)
        page = xutils.get_argument("page", 1, type=int)
        status = xutils.get_argument("status")
        offset = (page-1) * pagesize
        db = xtables.get_message_table()
        user_name = xauth.get_current_name()
        kw = "1=1"
        if status == "created":
            kw = "status = 0"
        if status == "done":
            kw = "status = 100"
        kw += " AND user = $user"
        vars = dict(user=xauth.get_current_name())
        chatlist = list(db.select(where=kw, vars=vars, order="ctime DESC", limit=pagesize, offset=offset))
        chatlist.reverse()
        amount = db.count(where=kw, vars=vars)
        page_max = math.ceil(amount / pagesize)
        return dict(code="success", message="", data=chatlist, amount=amount, page_max=page_max, current_user=xauth.get_current_name())

def update_message(id, status):
    db = xtables.get_message_table()
    msg = db.select_one(where=dict(id=id))
    if msg is None:
        return dict(code="fail", message="data not exists")
    if msg.user != xauth.get_current_name():
        return dict(code="fail", message="no permission")
    db.update(status=status, mtime=xutils.format_datetime(), where=dict(id=id))
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
        

class RemoveHandler:

    @xauth.login_required()
    def POST(self):
        id = xutils.get_argument("id")
        if id == "":
            return
        db = xtables.get_message_table()
        msg = db.select_one(where=dict(id=id))
        if msg is None:
            return dict(code="fail", message="data not exists")
        
        if msg.user != xauth.get_current_name():
            return dict(code="fail", message="no permission")
        db.delete(where=dict(id=id))
        return dict(code="success")


class CalendarRule(BaseRule):

    def execute(self, ctx, date, month, day):
        print(date, month, day)
        ctx.type = "calendar"


rules = [
    CalendarRule(r"(\d+)年(\d+)月(\d+)日")
]

class SaveHandler:

    @xauth.login_required()
    def POST(self):
        id        = xutils.get_argument("id")
        content   = xutils.get_argument("content")
        user_name = xauth.get_current_name()
        db = xtables.get_message_table()
        # 对消息进行语义分析处理，后期优化把所有规则统一管理起来
        ctx = Storage(content = content, user = user_name, type = "")
        for rule in rules:
            rule.match_execute(ctx, content)

        if id == "" or id is None:
            ctime = xutils.format_datetime()
            inserted_id = db.insert(content = content, 
                user = user_name, 
                ctime = ctime, 
                type = ctx.get("type", ""))
            return dict(code="success", data=dict(id=inserted_id, content=content, ctime=ctime))
        db.update(content = content,
            mtime = xutils.format_datetime(), 
            type=ctx.get("type", ""), 
            where=dict(id=id, user=user_name))
        return dict(code="success")

xurls=(
    "/file/message/add", SaveHandler,
    "/file/message/remove", RemoveHandler,
    "/file/message/update", SaveHandler,
    "/file/message/finish", FinishMessage,
    "/file/message/open", OpenMessage,
    "/file/message/list", ListHandler
)

