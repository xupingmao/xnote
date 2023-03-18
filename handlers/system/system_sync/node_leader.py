# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2022/02/12 18:13:41
# @modified 2022/04/18 23:22:15
# @filename node_leader.py

import threading
import time
import xauth
import xconfig
import xutils

from xutils import dateutil
from xutils import textutil
from xutils import Storage
from xutils import webutil
from xutils import dbutil
from xutils.db.binlog import BinLog

from .node_base import NodeManagerBase, convert_follower_dict_to_list
from .node_base import CONFIG
from .node_base import get_system_port

MAX_FOLLOWER_SIZE = 100
EXPIRE_TIME = 60 * 60


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


class Leader(NodeManagerBase):

    _lock = threading.RLock()
    FOLLOWER_DICT = dict()
    binlog = BinLog.get_instance()

    def get_follower_info(self, client_id):
        client_info = self.FOLLOWER_DICT.get(client_id)
        if client_info == None:
            client_info = FollwerInfo()
            client_info.init()
            client_info.client_id = client_id
            client_info.update_connect_info()
        return client_info

    def check_follower_count(self, client_id):
        if client_id not in self.FOLLOWER_DICT:
            return len(self.FOLLOWER_DICT) <= MAX_FOLLOWER_SIZE
        return True

    def update_follower_info(self, client_info):
        url = client_info.url
        self.FOLLOWER_DICT[url] = client_info

    def get_follower_list(self):
        follower_dict = self.FOLLOWER_DICT
        return convert_follower_dict_to_list(follower_dict)

    def get_follower_dict(self):
        return self.FOLLOWER_DICT

    def get_leader_url(self):
        return "http://127.0.0.1:%s" % get_system_port()

    def get_leader_node_id(self):
        return self.get_node_id()

    def get_leader_token(self):
        token = CONFIG.get("leader.token")
        if token is None or token == "":
            token = textutil.create_uuid()
            CONFIG.put("leader.token", token)

        return token

    def get_node_id(self):
        return xconfig.get("system.node_id")

    def get_ip_whitelist(self):
        return CONFIG.get("follower.whitelist", "")

    def sync_for_home_page(self):
        pass

    def get_fs_index_count(self):
        return xutils.call("system_sync.count_index")

    def get_system_version(self):
        return xconfig.get_global_config("system.version")

    def remove_expired_followers(self):
        for key in self.FOLLOWER_DICT.copy():
            info = self.FOLLOWER_DICT[key]
            if info.is_expired():
                del self.FOLLOWER_DICT[key]

    def get_leader_info(self):
        return dict(token=self.get_leader_token(),
                    node_id=self.get_node_id(),
                    fs_index_count=self.get_fs_index_count(),
                    system_version=self.get_system_version(),
                    binlog_last_seq=self.binlog.last_seq)

    def get_stat(self, port):
        admin_token = xauth.get_user_by_name("admin").token
        fs_index_count = self.get_fs_index_count()

        result = Storage()
        result.code = "success"
        result.timestamp = int(time.time())
        result.system_version = self.get_system_version()
        result.admin_token = admin_token
        result.fs_index_count = fs_index_count

        node_id = xutils.get_argument("node_id", "")

        client_ip = webutil.get_client_ip()
        url = "{ip}:{port}#{node_id}".format(
            ip=client_ip, port=port, node_id=node_id)

        with self._lock:
            if not self.check_follower_count(url):
                result.code = "403"
                result.message = "Too many connects"
                return result

            follower = self.get_follower_info(url)
            follower.update_ping_info()
            follower.fs_sync_offset = xutils.get_argument("fs_sync_offset", "")
            follower.fs_index_count = fs_index_count
            follower.admin_token = admin_token
            follower.node_id = node_id
            follower.url = url

            self.update_follower_info(follower)
            self.remove_expired_followers()

        result.follower_dict = self.get_follower_dict()
        result.leader = self.get_leader_info()

        return result

    def skip_db_sync(self, key:str):
        skipped_prefix_tuple = ("_binlog:", "_index$", "cluster_config:",
                                "fs_index:", "fs_sync_index:", "fs_sync_index_copy:")
        table_name = key.split(":", 1)[0]
        if table_name.find("$")>=0:
            return True
        return key.startswith(skipped_prefix_tuple)

    def list_binlog(self, last_seq, limit=20):
        sync_diff = self.binlog.last_seq - last_seq
        out_of_sync = sync_diff > self.binlog.count_size()

        if (last_seq <= 0) or (last_seq > self.binlog.last_seq) or out_of_sync:
            return dict(code="sync_broken", message="同步中断，请重新同步")

        def map_func(key, value):
            record_key = value.get("key")
            if self.skip_db_sync(record_key):
                return None
            table_name, seq = key.split(":")
            value["seq"] = int(seq)
            return value

        result = []
        binlogs = self.binlog.list(last_seq, limit, map_func=map_func)
        print("binlogs:", binlogs)
        has_next = len(binlogs)>=limit

        for log in binlogs:
            key = log.key
            log.value = dbutil.get(key)
            if log.value == None:
                log.optype = "delete"
                
            result.append(log)

        return dict(code="success", data=result, has_next = has_next)

    def list_db(self, last_key, limit=20):
        def filter_func(key, value):
            if self.skip_db_sync(key):
                return False
            return True

        result = []
        for key, value in dbutil.prefix_list("", key_from=last_key,
                                             limit=limit,
                                             include_key=True,
                                             scan_db=True,
                                             filter_func=filter_func):
            record = dict(key=key, value=value)
            result.append(record)
        return dict(binlog_last_seq=self.binlog.last_seq, rows=result)
