# encoding=utf-8
import time
from xutils import Storage, fsutil

class FileIndexInfo(Storage):
    """文件索引信息"""

    def __init__(self, **kw):
        self.id = kw.get("id", 0)
        self.webpath = kw.get("webpath", "")
        self.fpath = kw.get("fpath", "")
        self.mtime = kw.get("mtime", "")
        self.fsize = kw.get("fsize", 0)
        self.ftype = kw.get("ftype", "")
        self.last_try_time = kw.get("last_try_time", 0.0)

class LeaderStat(Storage):
    """主节点信息"""

    def __init__(self, **kw):
        self.code = "success"
        self.timestamp = int(time.time())
        self.system_version = ""
        self.admin_token = ""
        self.fs_index_count = 0
        self.follower_dict = {}
        super().__init__(**kw)


