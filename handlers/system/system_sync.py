# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/11/07 12:38:32
# @modified 2021/11/27 23:57:37
# @filename system_sync.py

"""系统数据同步功能，目前提供主从同步的能力

操作步骤：
1、启动主节点服务，在主节点上添加IP白名单
2、设置`--is_follower`参数启动子节点服务
3、配置子节点同步：
    a. 从主节点同步设置页面拷贝`同步链接`
    b. 把`同步链接`配置到子节点的同步设置页面上，点击同步按钮
4、配置完成后，系统开始同步
"""

import time
import threading
import xauth
import xutils
import xconfig
import xtemplate
import xmanager
from xutils import webutil
from xutils import Storage
from xutils import dbutil
from xutils import netutil
from xutils import dateutil
from xutils import textutil 

LOCK = threading.Lock()

def get_system_role():
    return xconfig.get_global_config("system.node.role")

def get_system_port():
    return xconfig.get_global_config("port")

dbutil.register_table("cluster_config", "集群配置")
CONFIG = dbutil.get_table("cluster_config", type = "hash")

MAX_FOLLOWER_SIZE = 100

def convert_follower_dict_to_list(follower_dict):
    follower_list = []
    for key in sorted(follower_dict.keys()):
        info = follower_dict.get(key)
        follower_list.append(Storage(**info))
    return follower_list

class NodeManagerBase:

    def get_leader_token(self):
        return CONFIG.get("leader.token")

    def get_ping_error(self):
        return None

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


class Follower(NodeManagerBase):

    def __init__(self):
        self.follower_list = []
        self.ping_error = None
    
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

    def get_follower_list(self):
        return self.follower_list

    def get_leader_url(self):
        return CONFIG.get("leader.host")

    def get_ping_error(self):
        return self.ping_error

LEADER = Leader()
FOLLOWER = Follower()

def get_system_role_manager():
    if get_system_role() == "leader":
        return LEADER
    else:
        return FOLLOWER

class ConfigHandler:

    def execute(self):
        key = xutils.get_argument("key")
        value = xutils.get_argument("value")

        if key == "leader.host":
            return self.set_leader_host(value)

        if key == "leader.token":
            return self.set_leader_token(value)

        return dict(code = "success")

    def set_leader_host(self, host):
        CONFIG.put("leader.host", host)
        return dict(code = "success")

    def set_leader_token(self, token):
        CONFIG.put("leader.token", token)
        return dict(code = "success")

def get_leader_url():
    if get_system_role() == "leader":
        return "127.0.0.1"

    return CONFIG.get("leader.host")

class SyncHandler:

    def POST(self):
        return self.GET()

    def GET(self):
        p = xutils.get_argument("p", "")
        client_ip = webutil.get_client_ip()
        system_role = get_system_role()

        # TODO：检查白名单和token
        # print("client_ip", client_ip)
        # client_ip_whitelist = xconfig.get_global_config("client.ip.whitelist", type = list)
        # if client_ip not in client_ip_whitelist:
        #     return dict(code = "403", message = "无权访问")

        if p == "home":
            return self.get_home_page()

        if p == "set-config":
            return self.do_set_config()

        if p == "ping":
            return self.do_ping()

        error = self.check_token()
        if error != None:
            return error

        if p == "get_token":
            return self.get_token()

        if p == "refresh_token":
            return self.refresh_token()

        # TODO 没有token不允许继续

        if p == "get_stat":
            return self.get_stat()

        if p == "list_files":
            return self.list_files()

        if p == "list_recent":
            return self.list_recent()

        return dict(code = "error", message = "未知的操作")

    def check_token(self):
        token = xutils.get_argument("token", "")
        leader_token = LEADER.get_leader_token()
        if token != leader_token:
            return dict(code = "403", message = "无权访问,TOKEN校验不通过")

    @xauth.login_required("admin")
    def get_home_page(self):
        kw = Storage()

        role_manager = get_system_role_manager()

        kw.node_role = get_system_role()
        kw.leader_host = CONFIG.get("leader.host", "未设置")
        kw.leader_token  = role_manager.get_leader_token()
        kw.leader_url    = role_manager.get_leader_url()
        kw.follower_list = role_manager.get_follower_list()
        kw.ping_error    = role_manager.get_ping_error()

        return xtemplate.render("system/page/system_sync.html", **kw)

    def do_set_config(self):
        handler = ConfigHandler()
        return handler.execute()

    def get_token():
        """通过临时令牌换取访问token"""
        pass

    def refresh_token():
        """刷新访问token"""
        pass

    def list_recent(self):
        result = Storage()
        result.code = "success"
        # TODO 读取filelist
        return result

    def list_files(self):
        result = Storage()
        result.code = "success"
        # TODO 读取filelist
        return result

    def get_stat(self):
        port = xutils.get_argument("port", "")
        result = Storage()
        result.code = "success"
        result.timestamp = int(time.time())
        result.system_version = xconfig.get_global_config("system.version")

        client_ip = webutil.get_client_ip()
        url = client_ip + ":" + port

        with LOCK:
            if not LEADER.check_follower_count(url):
                result.code = "403"
                result.message = "Too many connects"
                return result

            follower = LEADER.get_follower_info(url)
            follower.ping_time = dateutil.format_datetime()
            LEADER.update_follower_info(follower)

        result.follower_dict = LEADER.get_follower_dict()

        return result

    def do_ping(self):
        data = ping_leader()
        return dict(code = "success", data = data)

@xmanager.listen("sys.init")
def init(ctx = None):
    LEADER.get_leader_token()

@xmanager.listen("cron.minute")
def ping_leader(ctx = None):
    role = xconfig.get_global_config("system.node.role")
    if role == "leader":
        return None

    port = xconfig.get_global_config("system.port")
    leader_host  = CONFIG.get("leader.host")
    leader_token = CONFIG.get("leader.token")

    if leader_host != None:
        url = "{host}/system/sync?p=get_stat&port={port}&token={token}".format(
            host = leader_host, port = port, token = leader_token)

        result = netutil.http_get(url)
        result_obj = textutil.parse_json(result, ignore_error = True)
        print("PING主节点:", result_obj)
        
        FOLLOWER.update_ping_result(result_obj)

        return result_obj

    return None

xurls = (
    r"/system/sync", SyncHandler
)