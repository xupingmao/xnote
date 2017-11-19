# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/29
# 

"""短消息"""
import math
import xutils
import xtables
import xauth

class AddHandler:

    def POST(self):
        content = xutils.get_argument("content")
        user    = xauth.get_current_user()
        # chatlist.append(content)
        db = xtables.get_message_table()
        ctime = xutils.format_time()
        db.insert(user=user.get("name"), 
            ctime=ctime, 
            content=content)
        return dict(code="success", message="", data=dict(user=user.get("name"), content=content, ctime=ctime))

class ListHandler:

    def GET(self):
        pagesize = xutils.get_argument("pagesize", 20, type=int)
        page = xutils.get_argument("page", 1, type=int)
        offset = (page-1) * pagesize
        db = xtables.get_message_table()
        chatlist = list(db.select(order="status ASC, ctime DESC", limit=pagesize, offset=offset))
        chatlist.reverse()
        page_max = math.ceil(db.count() / pagesize)
        return dict(code="success", message="", data=chatlist, page_max=page_max, current_user=xauth.get_current_name())

class FinishMessage:

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
        db.update(status=1, where=dict(id=id))
        return dict(code="success")
        

class RemoveHandler:

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

xurls=(
    "/file/message/add", AddHandler,
    "/file/message/remove", RemoveHandler,
    "/file/message/finish", FinishMessage,
    "/file/message/list", ListHandler
)

