# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/11/07 12:38:32
# @modified 2022/03/31 12:21:54
# @filename system_sync_controller.py

"""系统数据同步功能，目前提供主从同步的能力

操作步骤：
1、启动主节点服务，在主节点上添加IP白名单
2、设置`node_role=follower`参数启动子节点服务
3、配置子节点同步：
    a. 从主节点同步设置页面拷贝`同步链接`
    b. 把`同步链接`配置到子节点的同步设置页面上，点击同步按钮
4、配置完成后，系统开始同步
"""

import time
import threading
import logging
import xutils
import web

from xnote.core import xauth, xconfig, xtemplate, xmanager

from xutils import webutil
from xutils import Storage
from xutils import dbutil
from xutils import dateutil
from xutils import textutil
from xutils import netutil
from xutils import cacheutil

from .node_follower import Follower
from .node_leader import Leader
from . import system_sync_indexer

dbutil.register_table("cluster_config", "集群配置")
CONFIG = dbutil.get_hash_table("cluster_config")


class SyncConfig:

    @staticmethod
    def need_sync_db():
        return xconfig.WebConfig.sync_db_from_leader
    
    @staticmethod
    def need_sync_files():
        return xconfig.WebConfig.sync_files_from_leader
    
    @staticmethod
    def set_need_sync_db(bool_value = False):
        xconfig.WebConfig.sync_db_from_leader = bool_value
    
    @staticmethod
    def set_need_sync_files(bool_value = False):
        xconfig.WebConfig.sync_files_from_leader = bool_value

def get_system_role():
    return xconfig.get_global_config("system.node_role")


def print_debug_info(*args):
    new_args = [dateutil.format_time(), "[system_sync]"]
    new_args += args
    print(*new_args)


def convert_dict_to_text(dict):
    return textutil.tojson(dict, format=True)


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

        if key == "reset_offset":
            return self.reset_offset()

        if key == "trigger_sync":
            return self.trigger_sync()
        
        if key == "sync_status":
            return self.set_sync_status(value)

        return dict(code="success")

    def reset_offset(self):
        FOLLOWER.reset_sync()
        return dict(code="success")

    def trigger_sync(self):
        FOLLOWER.ping_leader()
        FOLLOWER.sync_files_from_leader()
        return dict(code="success")

    def set_leader_host(self, host):
        assert xutils.is_str(host), "host is not str"

        if not netutil.is_http_url(host):
            return dict(code="400", message="无效的URL地址(%s)" % host)
        CONFIG.put("leader.host", host)
        cacheutil.delete("sync.leader_host")
        return dict(code="success")

    def set_leader_token(self, token):
        CONFIG.put("leader.token", token)
        cacheutil.delete("sync.leader_token")
        return dict(code="success")
    
    def set_sync_status(self, value):
        if value == None:
            return dict(code="err", message="配置值为空")
        bool_value = value.lower() == "true"
        SyncConfig.set_need_sync_db(bool_value)
        SyncConfig.set_need_sync_files(bool_value)
        if bool_value:
            message = "同步已开启"
        else:
            message = "同步已关闭"
        return dict(code="success", message=message)


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

        if p == "home" or p == "":
            return self.get_home_page()

        if p == "set_config":
            return self.do_set_config()

        if p == "ping":
            return self.do_ping()

        if p == "get_detail":
            return self.get_detail()

        if p == "build_index":
            if not xconfig.get_global_config("system.build_fs_sync_index"):
                return dict(code="403", message="文件同步索引未开启 [build_fs_sync_index]")

            return self.do_build_index()

        if p == "sync_files_from_leader":
            xauth.check_login("admin")
            return FOLLOWER.sync_files_from_leader()

        if p == "sync_db":
            xauth.check_login("admin")
            FOLLOWER.sync_db_from_leader()
            return webutil.SuccessResult()

        return LeaderHandler().handle_leader_action()
    
    def get_leader_binlog_seq(self, role_manager):
        leader_info = role_manager.get_leader_info()
        if leader_info == None:
            return -1
        return leader_info.get("binlog_last_seq")

    @xauth.login_required("admin")
    def get_home_page(self):
        kw = Storage()
        role_manager = get_system_role_manager()

        try:
            role_manager.sync_for_home_page()
        except:
            xutils.print_exc()

        kw.node_role = get_system_role()
        kw.leader_host = CONFIG.get("leader.host", "未设置")
        kw.leader_token = role_manager.get_leader_token()
        kw.leader_url = role_manager.get_leader_url()
        kw.leader_node_id = role_manager.get_leader_node_id()
        kw.leader_binlog_seq = self.get_leader_binlog_seq(role_manager)

        kw.follower_list = role_manager.get_follower_list()
        kw.ping_error = role_manager.get_ping_error()
        kw.fs_index_count = role_manager.get_fs_index_count()

        kw.whitelist = LEADER.get_ip_whitelist()
        kw.sync_process = FOLLOWER.get_sync_process()
        kw.sync_failed_count = FOLLOWER.count_sync_failed()
        kw.follower_binlog_seq = FOLLOWER.db_syncer.get_binlog_last_seq()
        kw.follower_db_sync_state = FOLLOWER.db_syncer.get_db_sync_state()
        kw.follower_db_last_key = FOLLOWER.db_syncer.get_db_last_key()
        kw.sync_status = SyncConfig.need_sync_db()

        return xtemplate.render("system/page/system_sync.html", **kw)

    @xauth.login_required("admin")
    def do_set_config(self):
        handler = ConfigHandler()
        return handler.execute()

    @xauth.login_required("admin")
    def get_detail(self):
        type = xutils.get_argument("type")
        key = xutils.get_argument("key")

        if type == "follower":
            role_manager = get_system_role_manager()
            info = role_manager.get_follower_info_by_url(key)
            return dict(code="success", data=info, text=convert_dict_to_text(info))

        return dict(code="500", message="未知的类型")

    def list_recent(self):
        result = Storage()
        result.code = "success"
        # TODO 读取filelist
        return result

    @xauth.login_required("admin")
    def do_build_index(self):
        manager = system_sync_indexer.FileSyncIndexManager()
        manager.build_full_index()
        return dict(code="success")

    def do_ping(self):
        data = FOLLOWER.ping_leader(force=True)
        return webutil.SuccessResult(data)


class LeaderHandler(SyncHandler):
    """作为主节点提供的能力"""

    def GET(self):
        return self.handle_leader_action()

    def get_token(self):
        """通过临时令牌换取访问token"""
        pass

    def refresh_token(self):
        """刷新访问token"""
        pass

    def check_token(self):
        token = xutils.get_argument("token", "")
        leader_token = LEADER.get_leader_token()
        if token != leader_token:
            error = dict(code="403", message="无权访问,TOKEN校验不通过")
            status = "401 Unauthorized"
            headers = {"Content-Type": "application/json"}
            raise web.HTTPError(status, headers, textutil.tojson(error))

    def list_files(self):
        """(主节点)读取文件列表"""
        last_id = xutils.get_argument_int("last_id", 0)
        result = Storage()
        result.code = "success"
        result.req_last_id = last_id

        data = system_sync_indexer.list_files(last_id=last_id)
        result.data = data
        return result

    def handle_leader_action(self):
        """主节点的提供的功能"""
        p = xutils.get_argument("p", "")
        error = self.check_token()
        if error != None:
            return error

        # 没有token不允许继续

        if p == "get_token":
            return self.get_token()

        if p == "refresh_token":
            return self.refresh_token()

        if p == "get_stat":
            port = xutils.get_argument("port", "")
            return LEADER.get_stat(port)

        if p == "list_files":
            return self.list_files()

        if p == "list_binlog":
            binlog_last_seq = xutils.get_argument_int("last_seq")
            limit = xutils.get_argument_int("limit", 20)
            include_req_seq = xutils.get_argument_bool("include_req_seq", True)
            return LEADER.list_binlog(binlog_last_seq, limit, include_req_seq=include_req_seq)

        if p == "list_db":
            last_key = xutils.get_argument("last_key", "")
            limit = xutils.get_argument_int("limit", 20)
            data = LEADER.list_db(last_key, limit)
            return dict(code="success", data=data)

        if p == "list_recent":
            return self.list_recent()

        return dict(code="error", message="未知的操作")


class FollowerHandler(SyncHandler):

    @xauth.login_required("admin")
    def GET(self):
        p = xutils.get_argument("p", "")
        if p == "get_leader_stat":
            return FOLLOWER.get_leader_info()
        
        return dict(code="400", message="unknown op")

@xmanager.listen("sys.init")
def init(ctx=None):
    LEADER.get_leader_token()

@xmanager.listen("sync.step")
# @log_mem_info_deco("on_ping_leader")
def on_ping_leader(ctx=None):
    role = get_system_role()
    if role == "leader":
        return None
    
    # TODO 优化ping的时间

    try:        
        if FOLLOWER.is_token_active():
            return
            
        return FOLLOWER.ping_leader()
    except:
        xutils.print_exc()
        logging.error("ping_leader failed, wait 60 seconds...")
        time.sleep(60)


@xmanager.listen("sync.step")
# @log_mem_info_deco("on_sync_files_from_leader")
def on_sync_files_from_leader(ctx=None):
    role = get_system_role()
    if role == "leader":
        return None
    
    if not SyncConfig.need_sync_files():
        return None
    
    if FOLLOWER.is_at_full_sync():
        # 优先等待db同步完
        return None

    try:
        logging.debug("开始同步文件...")
        logging.debug("-" * 50)
        FOLLOWER.sync_files_from_leader()
    except:
        xutils.print_exc()
        logging.error("sync_files_from_leader failed, wait 60 seconds...")
        time.sleep(60)


@xmanager.listen("sync.step")
# @log_mem_info_deco("on_sync_db_from_leader")
def on_sync_db_from_leader(ctx=None):
    role = get_system_role()
    if role == "leader":
        return None
    
    if not SyncConfig.need_sync_db():
        return None

    try:
        logging.debug("开始同步数据库")
        logging.debug("-"*50)
        FOLLOWER.sync_db_from_leader()
    except:
        xutils.print_exc()
        logging.error("sync_db_from_leader failed, wait 60 seconds...")
        time.sleep(60)

xurls = (
    r"/system/sync", SyncHandler,
    r"/system/sync/leader", LeaderHandler,
    r"/system/sync/follower", FollowerHandler,
)
