# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/10/06 12:24:41
# @modified 2022/04/09 22:10:00
# @filename message_model.py

from xutils import Storage

class MessageFolder(Storage):

    def __init__(self):
        self.date = ""
        self.wday = ""
        self.item_list = []

class MessageTag(Storage):

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

