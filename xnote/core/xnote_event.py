# encoding=utf-8
from xutils import Storage

class FileUploadEvent(Storage):
    """文件上传事件"""

    def __init__(self):
        self.user_name = ""
        self.user_id = 0
        self.fpath = ""


class FileDeleteEvent(FileUploadEvent):
    """文件删除事件"""
    pass

class FileRenameEvent(Storage):
    """文件重命名事件"""
    def __init__(self):
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


