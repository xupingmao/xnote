# encoding=utf-8
"""从节点管理"""

import time
import logging
import xutils
import xconfig

from xutils import Storage
from xutils import textutil
from xutils import dbutil
from .node_base import NodeManagerBase, convert_follower_dict_to_list, CONFIG

class Follower(NodeManagerBase):

    # PING的时间间隔，单位是秒
    PING_INTERVAL = 600

    def __init__(self):
        self.follower_list = []
        self.ping_error = None
        self.admin_token = None
        self.last_ping_time = -1
        self.fs_index_count = -1

    def get_client(self):
        leader_host = self.get_leader_url()
        leader_token = self.get_leader_token()
        return xutils.call("system_sync.HttpClient", leader_host, leader_token, self.admin_token)

    def ping_leader(self):
        now = time.time()
        if now - self.last_ping_time < self.PING_INTERVAL:
            logging.debug("没到PING时间")
            return

        port = xconfig.get_global_config("system.port")
        
        fs_sync_offset = CONFIG.get("fs_sync_offset", "")

        leader_host = self.get_leader_url()
        if leader_host != None:
            client = self.get_client()
            params = dict(port = port, fs_sync_offset = fs_sync_offset)
            result_obj = client.get_stat(params)

            logging.debug("PING主节点:%s", result_obj)
            
            self.update_ping_result(result_obj)

            self.last_ping_time = time.time()

            return result_obj

        return None
    
    def update_ping_result(self, result0):
        if result0 is None:
            return

        result = Storage(**result0)
        if result.code != "success":
            self.ping_error = result.message
            return

        self.ping_error = None
        follower_dict = result.get("follower_dict", {})
        self.follower_list = convert_follower_dict_to_list(follower_dict)

        if len(self.follower_list) > 0:
            item = self.follower_list[0]
            self.admin_token = item.admin_token
            self.fs_index_count = item.fs_index_count

    def get_follower_list(self):
        return self.follower_list

    def get_leader_url(self):
        return CONFIG.get("leader.host")

    def get_ping_error(self):
        return self.ping_error

    def sync_files_from_leader(self):
        self.ping_leader()

        if self.count_sync_done() >= self.fs_index_count:
            logging.debug("同步已经完成")
            return

        offset = CONFIG.get("fs_sync_offset", "")
        offset = textutil.remove_head(offset, "fs_sync_index:")

        logging.debug("offset:%s", offset)
        client = self.get_client()
        result = client.list_files(offset)
        if result is None:
            logging.error("返回结果为空")
            return

        if len(result.data) == 0:
            logging.debug("返回文件列表为空")
            return

        max_offset = offset
        for item in result.data:
            item = Storage(**item)
            key = item._key
            key = textutil.remove_head(key, "fs_sync_index:")
            max_offset = max(max_offset, key)

        # logging.debug("result:%s", result)
        client.download_files(result)

        # offset可能不变
        logging.debug("result.sync_offset:%s", result.sync_offset)
        logging.debug("max_offset:%s", max_offset)

        if max_offset != offset:
            CONFIG.put("fs_sync_offset", max_offset)

        return result

    def get_sync_process(self):
        if self.fs_index_count < 0:
            return "-1"

        count = self.count_sync_done()
        if count == 0:
            return "0%"
        return "%.2f%%" % (count / self.fs_index_count * 100.0)

    def sync_for_home_page(self):
        self.ping_leader()

    def get_fs_index_count(self):
        return self.fs_index_count

    def count_sync_done(self):
        return dbutil.count_table("fs_sync_index_copy")

    def count_sync_failed(self):
        return dbutil.count_table("fs_sync_index_failed")

    def reset_sync(self):
        CONFIG.put("fs_sync_offset", "")
        CONFIG.put("db_sync_offset", "")

        db = dbutil.get_hash_table("fs_sync_index_copy")
        for key, value in db.iter(limit = -1):
            db.delete(key)