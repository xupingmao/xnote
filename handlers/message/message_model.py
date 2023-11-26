# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/10/06 12:24:41
# @modified 2022/04/09 22:10:00
# @filename message_model.py

from xutils import Storage

"""消息模型相关的内容
任务：默认按照修改时间排序
记事/日记：默认按照创建时间排序
"""

class MessageFolder(Storage):

    def __init__(self):
        self.date = ""
        self.wday = ""
        self.item_list = []

class MessageTag(Storage):

    def __init__(self, 
            name = "", 
            tag = "", 
            amount = 0, 
            url = "", 
            mtime = "", **kw):
        self.name = name
        self.content = name
        self.amount = amount
        self.url = url
        self.mtime = mtime
        self.badge_info = ""
        self.update(kw)

def is_task_tag(tag):
    return tag in ("task", "done", "task.search", "done.search")
