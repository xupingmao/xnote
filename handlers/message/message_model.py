# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/10/06 12:24:41
# @modified 2022/04/09 22:10:00
# @filename message_model.py

import xutils
import typing

from xutils import Storage
from xutils import dateutil
from xutils import numutil
from xutils.functions import del_dict_key
from xnote.core.xtemplate import T
from xnote.core import xtables
from xnote.service import TagTypeEnum

"""消息模型相关的内容
任务：默认按照修改时间排序
记事/日记：默认按照创建时间排序
"""

VALID_MESSAGE_PREFIX_TUPLE = ("message:", "msg_key:", "msg_task:", "msg_v2:")
VALID_TAG_SET = set(["task", "done", "log", "key"])
# 带日期创建的最大重试次数
CREATE_MAX_RETRY = 20
MOBILE_LENGTH = 11

sys_comment_dict = {
    "$mark_task_done$": T("标记任务完成"),
    "$reopen_task$": T("重新开启任务"),
}

second_type_dict = {
    "log": 1,
    "task": 2,
    "done": 3,
}

class MessageSystemTag:
    """系统标签"""
    task = "task"
    done = "done"
    log = "log"
    key = "key"


class MessageFolder(Storage):

    def __init__(self):
        self.date = ""
        self.wday = ""
        self.item_list = []

class MessageTag(Storage):

    def __init__(self, **kw):
        self.name = ""
        self.content = kw.get("name", "")
        self.amount = 0
        self.url = ""
        self.mtime = xtables.DEFAULT_DATETIME
        self.badge_info = ""
        self.is_no_tag = False
        self.update(kw)


class MessageTagDO(Storage):

    def __init__(self, tag, size, priority=0):
        self.type = type
        self.size = size
        self.url = "/message?tag=" + tag
        self.priority = priority
        self.show_next = True
        self.is_deleted = 0
        self.name = "Message"
        self.icon = "fa-file-text-o"
        self.category = None
        self.badge_info = size

        if tag == "log":
            self.name = T("随手记")
            self.icon = "fa-file-text-o"

        if tag == "task":
            self.name = T("待办任务")
            self.icon = "fa-calendar-check-o"

    @classmethod
    def get_second_type_by_code(cls, code=""):
        return second_type_dict.get(code, 0)

def is_task_tag(tag):
    return tag in ("task", "done", "task.search", "done.search")


class MessageComment(Storage):
    def __init__(self):
        self.time = dateutil.format_datetime()
        self.content = ""

class MessageDO(Storage):
    def __init__(self):
        self._key = "" # kv的主键
        self._id = "" # kv的ID

        self.id = "" # 主键
        self.tag = "" # tag标签 {task, done, log, key}
        self.user = "" # 用户名
        self.user_id = 0 # 用户ID
        self.ip = ""
        self.ref = None # 引用的id
        self.ctime = xutils.format_datetime()  # 展示的创建时间
        self.ctime0 = xutils.format_datetime() # 实际的创建时间
        self.mtime = xutils.format_datetime()
        self.date = xutils.format_date()
        self.content = ""
        self.comments = [] # type: list[MessageComment] # 评论信息
        self.version = 0
        self.visit_cnt = 0
        self.status = None # 老的结构
        self.keywords = None # type: None|set[str]
        self.full_keywords = set()
        self.no_tag = True
        self.amount = 0 # keyword对象的数量
        self.done_time = None # type: str|None
        self.sort_value = ""

    @classmethod
    def from_dict(cls, dict_value: dict):
        result = MessageDO()
        result.update(dict_value)
        result.id = result._key
        if result.comments == None:
            result.comments = []
        for item in result.comments:
            comment_text = item.get("content")
            item["content"] = sys_comment_dict.get(comment_text, comment_text) # type:ignore
        
        if result.sort_value == "":
            result.sort_value = xtables.DEFAULT_DATETIME
            # index = MsgIndexDao.get_by_id(numutil.parse_int(result._id))
            # if index != None:
            #     result.sort_value = index.sort_value
            #     MessageDao.update(result)
            
        return result
    
    @classmethod
    def from_dict_list(cls, dict_list) -> typing.List["MessageDO"]:
        result = []
        for item in dict_list:
            result.append(cls.from_dict(item))
        return result
    
    @classmethod
    def from_dict_or_None(cls, dict_value):
        if dict_value == None:
            return None
        return cls.from_dict(dict_value)

    def check_before_update(self):
        id = self.id
        if not id.startswith(VALID_MESSAGE_PREFIX_TUPLE):
            raise Exception("[msg.update] invalid message id:%s" % id)

    def fix_before_update(self):
        if self.tag is None:
            # 修复tag为空的情况，这种一般是之前的待办任务，只有状态没有tag
            if self.status == 100:
                self.tag = "done"
            if self.status in (0, 50):
                self.tag = "task"

        del_dict_key(self, "html")
        del_dict_key(self, "tag_text")
        del_dict_key(self, "full_keywords")
        
        if self.status == None:
            self.pop("status", None)
        if self.amount == None:
            self.pop("amount", None)
        if self.ref == None:
            self.pop("ref", None)
        if self.keywords == None:
            self.pop("keywords", None)

    def check_before_create(self):
        if self.id != "":
            raise Exception("message.dao.create: can not set id")
        
        if self.user == "":
            raise Exception("message.dao.create: key `user` is missing")

        if self.ctime == "":
            raise Exception("message.dao.create: key `ctime` is missing")

        if self.tag != "done" and self.content == "":
            raise Exception("message.dao.create: key `content` is missing")

        if self.tag not in VALID_TAG_SET:
            raise Exception("message.dao.create: tag `%s` is invalid" % self.tag)
        
    def append_comment(self, comment_text=""):
        comment = MessageComment()
        comment.content = comment_text
        self.comments.append(comment)

    def get_int_id(self):
        return int(self._id)
    
    def get_second_type(self):
        return second_type_dict.get(self.tag, 0)


class MsgIndex(Storage):
    def __init__(self, **kw):
        self.id = 0
        self.tag = ""
        self.user_id = 0
        self.user_name = ""
        self.ctime_sys = dateutil.format_datetime() # 实际创建时间
        self.ctime = dateutil.format_datetime() # 展示创建时间
        self.mtime = dateutil.format_datetime() # 修改时间
        self.date = xtables.DEFAULT_DATE
        self.sort_value = "" # 排序字段, 对于log/task,存储创建时间,对于done,存储完成时间
        self.update(kw)

    @classmethod
    def from_dict(cls, dict_value):
        result = MsgIndex()
        result.update(dict_value)
        return result
    
    @classmethod
    def from_dict_list(cls, dict_list):
        return [cls.from_dict(item) for item in dict_list]
    
class MessageHistory:
    def __init__(self):
        self.msg_id = 0
        self.msg_version = 0
        self.user_id = 0
        self.content = ""
        self.ctime = dateutil.format_datetime()
