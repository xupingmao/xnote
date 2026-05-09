# encoding=utf-8
from xutils import Storage
from xutils.base import BaseEnum, EnumItem

class EventTypeEnum(BaseEnum):
    sys_reload = EnumItem("系统重新加载", "sys.reload")
    sys_init = EnumItem("系统初始化", "sys.init")

class FieldDesc:

    def __init__(self, field_name: str, field_type: str, *, not_empty = False):
        self.field_name = field_name
        self.field_type = field_type
        self.not_empty = not_empty

    def _is_empty(self, value):
        if self.field_type == "int":
            return value == 0
        if self.field_type == "str":
            return value == ""
        raise Exception(f"unknown type {self.field_type}")

    def validate(self, obj):
        if self.not_empty is False:
            return
        
        value = getattr(obj, self.field_name)
        if self.not_empty and self._is_empty(value):
            raise Exception(f"{self.field_name} is empty")
            

class BaseEvent(Storage):
    event_type = ""
    event_type_alias = []

    def __init__(self):
        super().__init__()
        self._fields = [] # type: list[FieldDesc]

    def add_field_desc(self, field_name: str, field_type:str, *, not_empty = True):
        field = FieldDesc(field_name=field_name, field_type=field_type, not_empty=not_empty)
        self._fields.append(field)

    def validate(self):
        if self.event_type == "":
            raise Exception("event_type is required")
        
        for field_desc in self._fields:
            field_desc.validate(self)

    def fire(self, is_async = None):
        self.validate()
        from xnote.core import xmanager
        xmanager.fire(self.event_type, self, is_async)

        for type_alias in self.event_type_alias:
            xmanager.fire(type_alias, self, is_async)

class FileUploadEvent(BaseEvent):
    """文件上传事件"""

    event_type = "fs.upload"

    def __init__(self):
        super().__init__()
        self.user_name = ""
        self.user_id = 0
        self.fpath = "" # real file path
        self.remark = ""

        self.add_field_desc("user_id", "int", not_empty=True)
        self.add_field_desc("fpath", "str", not_empty=True)

class FileDeleteEvent(FileUploadEvent):
    """文件删除事件"""
    event_type = "fs.delete"
    event_type_alias = ["fs.remove"]

class FileRenameEvent(BaseEvent):

    event_type = "fs.rename"

    """文件重命名事件"""
    def __init__(self):
        super().__init__()
        self.user_name = ""
        self.user_id = 0
        self.fpath = ""
        self.old_fpath = ""

        self.add_field_desc("user_id", "int", not_empty=True)
        self.add_field_desc("fpath", "str", not_empty=True)
        self.add_field_desc("old_fpath", "str", not_empty=True)

class NoteViewEvent(BaseEvent):
    """笔记访问事件"""
    event_type = "note.view"
    def __init__(self, id=0, user_name="", user_id=0):
        super().__init__()
        self.id = id
        self.user_name = user_name
        self.user_id = user_id


class MessageEvent(BaseEvent):
    """待办/随手记变更事件"""
    event_type = "message.updated"
    def __init__(self, msg_key="", user_id=0, tag="", content=""):
        super().__init__()
        self.msg_key = msg_key
        self.tag = tag
        self.user_id = user_id
        self.content = content

class MessageUpdateEvent(BaseEvent):
    event_type = "message.update"
    def __init__(self):
        super().__init__()
        self.msg_id = 0
        self.msg_key = ""
        self.user_id = 0
        self.content = ""


class UserUpdateEvent(BaseEvent):
    event_type = "user.update"
    def __init__(self):
        super().__init__()
        self.user_id = 0
        self.user_name = ""

class UserCreateEvent(BaseEvent):
    event_type = "user.create"
    def __init__(self):
        super().__init__()
        self.user_id = 0
        self.user_name = ""
