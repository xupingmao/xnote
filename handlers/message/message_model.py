# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/10/06 12:24:41
# @modified 2022/04/09 12:35:28
# @filename message_model.py

class MessageFolder:

    def __init__(self):
        self.date = ""
        self.wday = ""
        self.item_list = []

class MessageTag:

    def __init__(self, 
            name = None, 
            tag = None, 
            amount = None, 
            url = None, 
            mtime = None):
        self.name = name
        self.content = name
        self.amount = amount
        self.url = url
        self.mtime = mtime

