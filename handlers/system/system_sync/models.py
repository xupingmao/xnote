# encoding=utf-8

from xutils import Storage

class FileIndexInfo(Storage):

    def __init__(self, **kw):
        self.id = 0
        self.web_path = kw.get("web_path", "")
        self.fpath = kw.get("fpath", "")
        self.mtime = kw.get("mtime", 0)