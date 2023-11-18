# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2022/02/12 18:13:41
# @modified 2022/02/12 18:13:46
# @filename node_base.py


from xutils import dbutil, cacheutil
from xutils import Storage
from xnote.core import xconfig

"""节点管理的基类"""

dbutil.register_table("cluster_config", "集群配置")
CONFIG = dbutil.get_hash_table("cluster_config")

def get_system_port():
    return xconfig.get_global_config("port")

def format_http_url(url):
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return "http://" + url

def convert_follower_dict_to_list(follower_dict):
    follower_list = []
    for key in sorted(follower_dict.keys()):
        info = follower_dict.get(key)
        info = Storage(**info)
        info.http_url = format_http_url(info.url)
        follower_list.append(info)
    return follower_list


class NodeManagerBase:

    @cacheutil.cache_deco("sync.leader_token")
    def get_leader_token(self):
        return CONFIG.get("leader.token")

    def get_ping_error(self):
        return None
    
    def get_follower_list(self):
        raise NotImplementedError()

    def get_follower_info_by_url(self, url):
        for info in self.get_follower_list():
            if info.url == url or info.http_url == url:
                return info
        return None

