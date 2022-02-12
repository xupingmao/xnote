# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2022/02/12 18:13:41
# @modified 2022/02/12 18:13:57
# @filename node_leader.py

from xutils import dateutil
from xutils import textutil
from .node_base import NodeManagerBase, convert_follower_dict_to_list
from .node_base import CONFIG
from .node_base import get_system_port

class Leader(NodeManagerBase):
    FOLLOWER_DICT = dict()

    def get_follower_info(self, url):
        client_info = self.FOLLOWER_DICT.get(url)
        if client_info == None:
            client_info = Storage()
            client_info.url = url
            client_info.connected_time = dateutil.format_datetime()
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

