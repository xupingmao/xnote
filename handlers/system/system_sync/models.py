# encoding=utf-8
import time
import xutils
from xutils import Storage
from xutils import dateutil
from xnote.core import xtables
from datetime import datetime
from .config import EXPIRE_TIME

class FileIndexInfo(Storage):
    """文件索引信息 (用于数据同步) """
    def __init__(self, **kw):
        self.id = 0
        self.webpath = ""
        self.fpath = ""
        self.mtime = xtables.DEFAULT_DATETIME
        self.fsize = 0
        self.ftype = ""
        self.last_try_time = 0.0
        self.exists = True # 默认存在
        self.sha1_sum = ""
        self.update(kw)


class FollwerInfo(Storage):

    def init(self):
        self.ping_time_ts = time.time()

    def update_connect_info(self):
        self.connected_time = dateutil.format_datetime()
        self.connected_time_ts = time.time()

    def is_expired(self):
        gap = time.time() - self.ping_time_ts
        return gap > EXPIRE_TIME

    def update_ping_info(self):
        self.ping_time = dateutil.format_datetime()
        self.ping_time_ts = time.time()


class LeaderStat(Storage):
    """主节点信息"""

    def __init__(self, **kw):
        self.code = "success"
        self.timestamp = int(time.time())
        self.system_version = ""
        self.admin_token = ""
        self.access_token = ""
        self.fs_index_count = 0
        self.fs_max_index = 0
        self.follower_dict = {} # type: dict[str, FollwerInfo]
        super().__init__(**kw)

    @classmethod
    def from_dict(cls, dict_value):
        if dict_value == None:
            return None
        result = LeaderStat()
        result.update(dict_value)
        return result


class SystemSyncToken(Storage):

    def __init__(self):
        self.id = 0
        self.token_holder = ""
        self.token = ""
        self.ctime = xtables.DEFAULT_DATETIME
        self.mtime = xtables.DEFAULT_DATETIME
        self.expire_time = xtables.DEFAULT_DATETIME

    @classmethod
    def from_dict(cls, dict_value):
        if dict_value == None:
            return None
        result = SystemSyncToken()
        result.update(dict_value)
        return result

    def is_expired(self):
        now = datetime.now()
        expire_time = dateutil.to_py_datetime(self.expire_time)
        return expire_time <= now