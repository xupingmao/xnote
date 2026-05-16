# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/10/06 12:24:41
# @modified 2022/04/09 22:10:00
# @filename message_model.py

import xutils
import typing

from xutils import Storage, BaseDataRecord
from xutils import dateutil
from xutils.functions import del_dict_key, delete_None_values
from xnote.core.xtemplate import T
from xnote.core import xtables, xconfig
from xnote.service import TagTypeEnum, TagInfoDO
from xutils.db.dbutil_helper import new_from_dict
from xutils.base import BaseEnum, EnumItem
from xnote.service.tag_service import SystemTagEnum
from xnote_handlers.config import LinkConfig
from xutils import quote
from typing import List

"""消息模型相关的内容
任务：默认按照修改时间排序
记事/日记：默认按照创建时间排序
"""

VALID_MESSAGE_PREFIX_TUPLE = ("message:", "msg_key:", "msg_task:", "msg_v3:")
VALID_TAG_SET = set(["task", "done", "log", "key"])
# 带日期创建的最大重试次数
CREATE_MAX_RETRY = 20
MOBILE_LENGTH = 11

sys_comment_dict = {
    "$mark_task_done$": T("标记任务完成"),
    "$reopen_task$": T("重新开启任务"),
}

class BaseMsgDO(Storage):
    def get_time_info(self):
        return ""

server_home = xconfig.WebConfig.server_home

class MessageTagItem(EnumItem):

    def __init__(self, name="", value=""):
        super().__init__(name, value)

    @property
    def url(self):
        return f"{server_home}/message/tag/system_tag?tag_code={self.value}"

class MessageTagEnum(BaseEnum):
    task = MessageTagItem(name="任务", value="task")
    done = MessageTagItem(name="完成", value="done")
    log = MessageTagItem(name="随手记", value="log")

    book = MessageTagItem("书籍", "_book")
    people = MessageTagItem("人物", "_people")
    file = MessageTagItem("文件", "_file")
    phone = MessageTagItem("电话", "_phone")
    link = MessageTagItem("链接", "_link")

    system_tag_list = [file, link, book, people, phone]
    first_tag_list = [task, done, log]

    @classmethod
    def is_first_tag_code(cls, tag_code=""):
        for item in cls.first_tag_list:
            if tag_code == item.value:
                return True
        return False

    @classmethod
    def is_system_tag_code(cls, tag_code=""):
        for item in cls.system_tag_list:
            if tag_code == item.value:
                return True
        return False

class MessageSecondTypeEnum(BaseEnum):
    """随手记标签的二级类型"""
    
    log = EnumItem("log", "1")
    task = EnumItem("task", "2")
    done = EnumItem("done", "3")

    _enums = [log, task, done]

    @classmethod
    def get_type_by_name(cls, name=""):
        for item in cls._enums:
            if item.name == name:
                return item.int_value
        return 0

class MessageFolder(Storage):

    def __init__(self):
        self.date = ""
        self.wday = ""
        self.title = ""
        self.css_class = ""
        self.item_list = []

class MsgTagInfo(TagInfoDO):
    """用户标签"""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.search_tag = ""
        self.html = ""
        self.custom_url = kw.get("url", "")
        self.badge_info = ""
        self.update(kw)

    @property
    def content(self):
        return SystemTagEnum.get_name_by_code(self.tag_code)
    
    @property
    def is_marked(self):
        return self.score == 1.0
    
    @property
    def tag(self):
        return "key"
    
    @property
    def is_standard(self):
        tag_code = self.tag_code
        return tag_code.startswith("#") and tag_code.endswith("#")
    
    @property
    def is_sys_tag(self):
        return SystemTagEnum.is_sys_tag(self.tag_code)
    
    def set_is_marked(self, value=False):
        if value:
            self.score = 1.0
        else:
            self.score = 0.0

    def to_save_dict(self):
        result = dict(**self)
        result.pop("tag_id", None)
        result.pop("tag_name", None)
        result.pop("html", None)
        result.pop("search_tag", None)
        result.pop("custom_url", None)
        result.pop("badge_info", None)
        return result
    
    def get_time_info(self):
        return self.ctime
    
    @property
    def name(self):
        return self.tag_name
    
    @property
    def url(self):
        if SystemTagEnum.is_sys_tag(self.tag_code):
            return f"/message/tag/list?tag=log.tags&sys_tag={self.tag_code}"
        
        if self.custom_url != "":
            return self.custom_url
        
        if self.search_tag != "":
            return f"/message?tag={self.search_tag}&key={quote(self.tag_code)}"
        return f"/message?tag=search&key={quote(self.tag_code)}"

MessageTag = MsgTagInfo

class MessageStatItem(BaseMsgDO):
    """这个是对外展示的菜单信息"""
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
            self.url = LinkConfig.task_list.href

    @classmethod
    def get_second_type_by_code(cls, code=""):
        return MessageSecondTypeEnum.get_type_by_name(code)

def is_task_tag(tag: str):
    return tag in ("task", "done", "task.search", "done.search")


class MessageComment(BaseDataRecord):
    def __init__(self):
        self.time = dateutil.format_datetime()
        self.content = ""

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
        self.change_time = xtables.DEFAULT_DATETIME # 状态变更的时间，比如创建时间/完成时间/重新打开的时间
        self.update(kw)

    @classmethod
    def from_dict(cls, dict_value):
        result = MsgIndex()
        result.update(dict_value)
        return result
    
    @classmethod
    def from_dict_list(cls, dict_list):
        return [cls.from_dict(item) for item in dict_list]

class QuerySourceType:
    heading_tag = "heading_tag"

class MessageDO(BaseMsgDO):
    tag_text: str
    
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
        self.full_keywords = set() # 包括普通的hashtag和书名号等在内的默认实体
        self.system_tags = [] # 系统标签
        self.no_tag = True
        self.amount = 0 # keyword对象的数量
        self.done_time = None # type: str|None
        self.change_time = xtables.DEFAULT_DATETIME
        self.html = ""
        self.query_source = ""
        self.query_key = ""
        self.files: List[str] = [] # 上传的文件

    @classmethod
    def from_dict(cls, dict_value: dict):
        result = MessageDO()
        result.update(dict_value)
        result.id = result._key
        if result.comments == None:
            result.comments = []
        result.comments = MessageComment.from_dict_list(result.comments)
        for item in result.comments:
            comment_text = item.get("content")
            item["content"] = sys_comment_dict.get(comment_text, comment_text) # type:ignore
        return result
    
    @classmethod
    def from_dict_list(cls, dict_list):
        return [cls.from_dict(item) for item in dict_list]
    
    @classmethod
    def from_dict_or_None(cls, dict_value):
        if dict_value == None:
            return None
        return cls.from_dict(dict_value)

    def check_before_update(self):
        id = self.id
        if not id.startswith(VALID_MESSAGE_PREFIX_TUPLE):
            raise Exception("[msg.update] invalid message id:%s" % id)

    def fix_before_save(self):
        if self.tag is None:
            # 修复tag为空的情况，这种一般是之前的待办任务，只有状态没有tag
            if self.status == 100:
                self.tag = "done"
            if self.status in (0, 50):
                self.tag = "task"

        del_dict_key(self, "html")
        del_dict_key(self, "tag_text")
        del_dict_key(self, "full_keywords")
        del_dict_key(self, "system_tags")
        del_dict_key(self, "query_source")
        del_dict_key(self, "query_key")

        # remove None values
        delete_None_values(self)

    def check_before_create(self):
        if self.id != "":
            raise Exception("message.dao.create: can not set id")
        
        if self.user == "":
            raise Exception("message.dao.create: key `user` is missing")

        if self.ctime == "":
            raise Exception("message.dao.create: key `ctime` is missing")

        if self.tag != "done" and self.content == "" and len(self.files) == 0:
            raise Exception("message.dao.create: key `content` or `files` is empty")

        if self.tag not in VALID_TAG_SET:
            raise Exception("message.dao.create: tag `%s` is invalid" % self.tag)
        
    def append_comment(self, comment_text=""):
        comment = MessageComment()
        comment.content = comment_text
        self.comments.append(comment)

    def get_int_id(self):
        return int(self._id)
    
    @property
    def int_id(self):
        return int(self._id)
    
    def get_second_type(self):
        return MessageSecondTypeEnum.get_type_by_name(self.tag)
    
    def get_time_info(self):
        if is_task_tag(self.tag):
            return self.change_time
        else:
            return self.ctime
        
    def update_index(self, index: MsgIndex):
        self.tag = index.tag
        self.change_time = index.change_time
        self.user_id = index.user_id
        self.ctime = index.ctime
        self.mtime = index.mtime
        
    @classmethod
    def from_index(cls, index: MsgIndex):
        result = MessageDO()
        key = f"msg_v3:{index.id}"
        result.id = key
        result._id = str(index.id)
        result._key = key
        result.content = "[数据已丢失]"
        result.update_index(index)
        return result
    
class MessageHistory:
    def __init__(self):
        self.msg_id = 0
        self.msg_version = 0
        self.user_id = 0
        self.content = ""
        self.ctime = dateutil.format_datetime()


class MessageTemplateRecord(BaseDataRecord):
    _ignore_save_fields = ["template_id"]

    def __init__(self):
        now = dateutil.format_datetime()
        self.template_id = 0
        self.type = "log"
        self.ctime = now
        self.mtime = now
        self.user_id = 0
        self.name = ""
        self.content = ""
        self.sort_num = 0
        self.version = 0

class MessageStatDO(xutils.Storage):
    def __init__(self, **kw):
        self.task_count = 0
        self.log_count = 0
        self.done_count = 0
        self.cron_count = 0
        self.key_count = 0
        self.canceled_count = 0
        self.search_count = 0
        self.update(kw)

class MessageStatVO(xutils.Storage):
    def __init__(self, **kw):
        self.task_count = ""
        self.log_count = ""
        self.done_count = ""
        self.cron_count = ""
        self.key_count = ""
        self.canceled_count = ""
        self.search_count = ""
        self.update(kw)
