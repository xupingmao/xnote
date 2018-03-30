# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/29
# @since 2017/08/04
# @modified 2018/03/31 01:14:55

"""短消息"""
import re
import math
import xutils
import xtables
import xauth
import xconfig
import xmanager
import xtemplate
from xutils import BaseRule, Storage

def process_html(message):
    """简单的处理HTML"""
    content = message.content
    # \xad (Soft hyphen), 用来处理断句的
    content = content.replace(u'\xad', '\n')

    lines = []
    for line in content.split("\n"):
        if line.startswith("file://"):
            href = line[7:]
            if line.endswith((".jpg", ".jpeg", ".png", ".gif")):
                line = '<a href="%s"><img class="chat-msg-img" src="%s"></a>' % (href, href)
            else:
                line = '<a href="%s">%s</a>' % (href, href)
        else:
            line = re.sub(r"https?://[^\s]+", '<a href="\\g<0>">\\g<0></a>', line)
            line = line.replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;")
            # TODO 处理空格的问题
            # line = line.replace(" ", "&nbsp;")
        lines.append(line)
    message.html = "<br/>".join(lines)
    return message


class ListHandler:

    def GET(self):
        pagesize = xutils.get_argument("pagesize", xconfig.PAGE_SIZE, type=int)
        page   = xutils.get_argument("page", 1, type=int)
        status = xutils.get_argument("status")
        key    = xutils.get_argument("key")
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
        if key != "" and key != None:
            kw += " AND content LIKE $content"
            vars["content"] = '%' + key + '%'
            chatlist = list(db.select(where=kw, vars=vars, order="ctime DESC", limit=pagesize, offset=offset))
        else:
            chatlist = list(db.select(where=kw, vars=vars, order="ctime DESC", limit=pagesize, offset=offset))
        chatlist.reverse()
        amount = db.count(where=kw, vars=vars)
        page_max = math.ceil(amount / pagesize)
        chatlist = list(map(process_html, chatlist))
        return dict(code="success", message="", data=chatlist, amount=amount, page_max=page_max, current_user=xauth.get_current_name())

def update_message(id, status):
    db = xtables.get_message_table()
    msg = db.select_one(where=dict(id=id))
    if msg is None:
        return dict(code="fail", message="data not exists")
    if msg.user != xauth.get_current_name():
        return dict(code="fail", message="no permission")
    xmanager.fire("message.update", Storage(id=id, status=status, user = msg.user, content=msg.content))
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
        xmanager.fire("message.update", Storage())
        return dict(code="success")


class CalendarRule(BaseRule):

    def execute(self, ctx, date, month, day):
        print(date, month, day)
        ctx.type = "calendar"

def expire_message_cache(ctx):
    user = ctx.user
    xutils.expire_cache(prefix="message.count", args=(user,))

xmanager.set_handlers('message.update', [expire_message_cache])

rules = [
    CalendarRule(r"(\d+)年(\d+)月(\d+)日"),
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
        xmanager.fire('message.update', ctx)

        if id == "" or id is None:
            ctime = xutils.get_argument("date", xutils.format_datetime())
            inserted_id = db.insert(content = content, 
                user = user_name, 
                status = 100,
                mtime = ctime,
                ctime = ctime)
            return dict(code="success", data=dict(id=inserted_id, content=content, ctime=ctime))
        db.update(content = content,
            mtime = xutils.format_datetime(), 
            where=dict(id=id, user=user_name))
        return dict(code="success")

class DateHandler:

    @xauth.login_required()
    def GET(self):
        date = xutils.get_argument("date")
        db = xtables.get_message_table()
        data = db.select(where="ctime LIKE $date AND user=$user", 
            vars = dict(date = date + '%', user=xauth.get_current_name()))
        return dict(code="success", data = list(data))

class MessageHandler:

    @xauth.login_required()
    def GET(self):
        return xtemplate.render("message/message.html", 
            search_action="/message", 
            search_placeholder="搜索短消息",
            key = xutils.get_argument("key", ""))


xurls=(
    r"/file/message/add", SaveHandler,
    r"/file/message/remove", RemoveHandler,
    r"/file/message/update", SaveHandler,
    r"/file/message/finish", FinishMessage,
    r"/file/message/open", OpenMessage,
    r"/file/message/list", ListHandler,
    r"/file/message/date", DateHandler,
    r"/message", MessageHandler,
)

