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
from .node_base import NodeManagerBase, convert_follower_dict_to_list
from .node_base import CONFIG
from .node_base import get_system_port

LOCK = threading.RLock()
MAX_FOLLOWER_SIZE = 100
EXPIRE_TIME = 60 * 60

class FollwerInfo(Storage):

    def init(self):
        self.ping_time_ts = time.time()

    def connect(self):
        self.connected_time = dateutil.format_datetime()
        self.connected_time_ts = time.time()

    def is_expired(self):
        gap = time.time() - self.ping_time_ts
        return gap > EXPIRE_TIME

    def ping(self):
        self.ping_time = dateutil.format_datetime()
        self.ping_time_ts = time.time()

class Leader(NodeManagerBase):
    FOLLOWER_DICT = dict()

    def get_follower_info(self, url):
        client_info = self.FOLLOWER_DICT.get(url)
        if client_info == None:
            client_info = FollwerInfo()
            client_info.init()
            client_info.url = url
            client_info.connect()
        return client_info

    def check_follower_count(self, url):
        if url not in self.FOLLOWER_DICT:
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

    def get_leader_token(self):
        token = CONFIG.get("leader.token")
        if token is None or token == "":
            token = textutil.create_uuid()
            CONFIG.put("leader.token", token)

        return token

    def get_ip_whitelist(self):
        return CONFIG.get("follower.whitelist", "")

    def sync_for_home_page(self):
        pass

    def get_fs_index_count(self):
        return xutils.call("system_sync.count_index")

    def remove_expired_followers(self):
        for key in self.FOLLOWER_DICT.copy():
            info = self.FOLLOWER_DICT[key]
            if info.is_expired():
                del self.FOLLOWER_DICT[key]

    def get_stat(self, port):
        admin_token = xauth.get_user_by_name("admin").token
        fs_index_count = self.get_fs_index_count()

        result = Storage()
        result.code = "success"
        result.timestamp = int(time.time())
        result.system_version = xconfig.get_global_config("system.version")
        result.admin_token = admin_token
        result.fs_index_count = fs_index_count

        client_ip = webutil.get_client_ip()
        url = client_ip + ":" + port

        with LOCK:
            if not self.check_follower_count(url):
                result.code = "403"
                result.message = "Too many connects"
                return result

            follower = self.get_follower_info(url)
            follower.ping()
            follower.fs_sync_offset = xutils.get_argument("fs_sync_offset", "")
            follower.fs_index_count = fs_index_count
            follower.admin_token = admin_token

            self.update_follower_info(follower)
            self.remove_expired_followers()

        result.follower_dict = self.get_follower_dict()

        return result

