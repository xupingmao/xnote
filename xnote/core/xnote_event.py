# encoding=utf-8
from xutils import Storage

class FileUploadEvent(Storage):
    """文件上传事件"""

    def __init__(self):
        super().__init__()
        self.user_name = ""
        self.user_id = 0
        self.fpath = ""
        self.remark = ""


class FileDeleteEvent(FileUploadEvent):
    """文件删除事件"""
    pass

class FileRenameEvent(Storage):
    """文件重命名事件"""
    def __init__(self):
        super().__init__()
        self.user_name = ""
        self.user_id = 0
        self.fpath = ""
        self.old_fpath = ""

class NoteViewEvent(Storage):
    """笔记访问事件"""
    def __init__(self, id=0, user_name="", user_id=0):
        super().__init__()
        self.id = id
        self.user_name = user_name
        self.user_id = user_id


class MessageEvent(Storage):
    """待办/随手记变更事件"""
    def __init__(self, msg_key="", user_id=0, tag="", content=""):
        super().__init__()
        self.msg_key = msg_key
        self.tag = tag
        self.user_id = user_id
        self.content = content