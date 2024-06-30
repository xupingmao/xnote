

from xutils import dateutil
from xutils import dbutil
from xutils import cacheutil
from xnote.core import xtables
from .models import SystemSyncToken

class SystemSyncTokenDao:

    db = xtables.get_table_by_name("system_sync_token")

    @classmethod
    def get_by_holder(cls, token_holder=""):
        dict_result = cls.db.select_first(where=dict(token_holder=token_holder))
        return SystemSyncToken.from_dict(dict_result)

    @classmethod
    def get_by_token(cls, token=""):
        dict_result = cls.db.select_first(where=dict(token=token))
        return SystemSyncToken.from_dict(dict_result)

    @classmethod
    def upsert(cls, token_info: SystemSyncToken):
        if token_info.id == 0:
            token_info.ctime = dateutil.format_datetime()
            token_info.mtime = dateutil.format_datetime()
            inserts = token_info.copy()
            inserts.pop("id", None)
            return cls.db.insert(**inserts)
        else:
            token_info.mtime = dateutil.format_datetime()
            return cls.db.update(**token_info, where=dict(id=token_info.id))

dbutil.register_table("cluster_config", "集群配置")

class ClusterConfigDao:
    db = dbutil.get_hash_table("cluster_config")

    @classmethod
    def get_leader_token(cls):
        result = cls.db.get("leader.token", default_value="")
        assert isinstance(result, str)
        return result
    
    @classmethod
    def put_leader_token(cls, token):
        cls.db.put("leader.token", token)

    @classmethod
    def put_leader_host(cls, host):
        cls.db.put("leader.host", host)
        cacheutil.delete("sync.leader_host")

    @classmethod
    def get_leader_host(cls):
        # TODO cache
        result = cls.db.get("leader.host", default_value="")
        assert isinstance(result, str)
        return result
    
    @classmethod
    def get_fs_sync_last_id(cls):
        value = cls.db.get("fs_sync_last_id")
        try:
            return int(value)
        except:
            return 0
        
    @classmethod
    def put_fs_sync_last_id(cls, last_id):
        cls.db.put("fs_sync_last_id", last_id)

    @classmethod
    def reset_sync(cls):
        CONFIG = cls.db
        CONFIG.put("fs_sync_offset", "")
        CONFIG.put("db_sync_offset", "")
        CONFIG.put("follower_db_sync_state", "full")
        CONFIG.delete("follower_binlog_last_seq")
        CONFIG.delete("follower_db_last_key")
    
    @classmethod
    def get_binlog_last_seq(cls):
        value = cls.db.get("follower_binlog_last_seq", 0)
        if isinstance(value, int):
            return value
        return 0
    
    @classmethod
    def put_binlog_last_seq(cls, last_seq):
        return cls.db.put("follower_binlog_last_seq", last_seq)

    @classmethod
    def get_db_sync_state(cls):
        return cls.db.get("follower_db_sync_state", "full")

    @classmethod
    def put_db_sync_state(cls, state):
        assert state in ("full", "binlog")
        cls.db.put("follower_db_sync_state", state)
    
    @classmethod
    def get_db_last_key(cls):
        # type: () -> str
        # 全量同步使用，按照key进行遍历
        value = cls.db.get("follower_db_last_key", "")
        assert isinstance(value, str)
        return value

    @classmethod
    def put_db_last_key(cls, last_key):
        cls.db.put("follower_db_last_key", last_key)


    @classmethod
    def get_follower_whitelist(cls):
        return cls.db.get("follower.whitelist", "")