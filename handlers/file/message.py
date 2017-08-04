# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/05/29
# 

"""短消息"""
import xutils
import xtables
import xauth

class AddHandler:

    def POST(self):
        content = xutils.get_argument("content")
        user    = xauth.get_current_user()
        # chatlist.append(content)
        db = xtables.get_message_table()
        db.insert(user=user.get("name"), 
            ctime=xutils.format_time(), 
            content=content)
        return dict(code="success", message="", data=dict(user=user.get("name"), content=content))

class ListHandler:

    def GET(self):
        db = xtables.get_message_table()
        chatlist = list(db.select(order="ctime DESC", limit=20))
        chatlist.reverse()
        return dict(code="success", message="", data=chatlist)

xurls=( "/file/message/add", AddHandler,
        "/file/message/list", ListHandler)

