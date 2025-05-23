# encoding=utf-8
import time
import xutils
import typing

from xutils import BaseDataRecord
from xutils import Storage
from xutils import dateutil
from xnote.core import xtables
from datetime import datetime
from .config import EXPIRE_TIME

class ResultCode:
    success = "success"
    sync_broken = "sync_broken" # 同步损坏


class FileIndexInfo(Storage):
    """文件索引信息 (用于数据同步) """
    def __init__(self, **kw):
        self.id = 0
        self.webpath = ""
        self.fpath = ""
        self.mtime = xtables.DEFAULT_DATETIME
        self.user_id = 0
        self.fsize = 0
        self.ftype = ""
        self.last_try_time = 0.0
        self.exists = True # 默认存在
        self.sha1_sum = ""
        self.update(kw)

class FollowerInfo(BaseDataRecord):

    def __init__(self, **kw):
        self.ping_time_ts = time.time()
        self.node_id = ""
        self.http_url = ""
        self.url = ""
        self.client_id = ""
        self.admin_token = ""
        self.fs_index_count = 0
        self.fs_sync_offset = ""
        self.update(kw)

    def init(self):
        pass

    def update_connect_info(self):
        self.connected_time = dateutil.format_datetime()
        self.connected_time_ts = time.time()

    def is_expired(self):
        gap = time.time() - self.ping_time_ts
        return gap > EXPIRE_TIME

    def update_ping_info(self):
        self.ping_time = dateutil.format_datetime()
        self.ping_time_ts = time.time()

    @classmethod
    def from_dict_dict(cls, dd):
        result = {} # type: dict[str, FollowerInfo]
        if dd is None:
            return result
        for k in dd:
            value = dd[k]
            result[k] = cls.from_dict(value)
        return result

class LeaderBaseInfo(BaseDataRecord):
    def __init__(self, **kw):
        self.token = ""
        self.node_id = ""
        self.fs_index_count = 0
        self.system_version = ""
        self.binlog_last_seq = 0
        super().__init__(**kw)

class LeaderStat(Storage):
    """主节点信息"""

    def __init__(self, **kw):
        self.code = "success"
        self.message = ""
        self.node_id = ""
        self.timestamp = int(time.time())
        self.system_version = ""
        self.admin_token = ""
        self.access_token = ""
        self.fs_index_count = 0 # 服务器文件索引数量
        self.fs_max_index = 0   # 服务器文件最大的索引
        self.follower_dict = {} # type: dict[str, FollowerInfo]
        self.leader = None  # type: LeaderBaseInfo | None
        super().__init__(**kw)

    @classmethod
    def from_dict(cls, dict_value: typing.Optional[dict]):
        if dict_value == None:
            return None
        result = LeaderStat()
        result.update(dict_value)
        result.follower_dict = FollowerInfo.from_dict_dict(result.follower_dict)
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
    
