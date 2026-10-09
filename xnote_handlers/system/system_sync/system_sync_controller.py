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
import typing

from xnote.core import xauth, xconfig, xtemplate, xmanager
from xnote.plugin import TabBox
from xnote.plugin.list_plugin import BaseListPlugin
from xnote.webui import ListView, ListViewItem, TextSpan, TextTag, ActionButton, Card
from xnote.service.system_meta_service import SystemMetaEnum

from xutils import webutil
from xutils import Storage
from xutils import dateutil
from xutils import textutil
from xutils import netutil
from . import system_sync_indexer
from .dao import SystemSyncTokenDao
from xnote_handlers.system.system_sync.dao import ClusterConfigDao
from xnote.core.xtemplate import T
from xnote_handlers.config import LinkConfig
from .system_sync_instances import LeaderInstance, FollowerInstance
from . import system_sync_open_api
from .node_leader import Leader
from .node_follower import Follower
from .models import FollowerInfo

system_sync_open_api.init()

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

    @classmethod
    def is_leader(cls):
        return xconfig.WebConfig.is_leader()


class SystemSyncHomeModel:
    """集群管理首页的数据模型，替代原先松散的 Storage() 字典，字段类型明确"""

    def __init__(self) -> None:
        # 节点角色信息
        self.node_role: str = ""
        self.is_leader: bool = False

        # 主节点信息
        self.leader_host: str = ""
        self.leader_token: str = ""
        self.leader_url: str = ""
        self.leader_node_id: str = ""
        self.leader_binlog_seq: int = 0

        # 集群信息
        self.follower_list: typing.List[FollowerInfo] = []
        self.ping_error: typing.Optional[str] = None

        # 文件索引 / 配置
        self.fs_index_count: int = 0
        self.whitelist: str = ""
        self.sync_process: str = ""

        # 从节点 DB 同步状态
        self.follower_binlog_seq: int = 0
        self.follower_db_sync_state: str = ""
        self.follower_db_last_key: str = ""

        # 同步开关
        self.sync_status: bool = False

        # 从节点专有：文件同步进度
        self.fs_max_index: int = 0
        self.fs_current_index: int = 0
        self.fs_sync_failed_msg: str = ""

        # 渲染产物（各区块组件）
        self.leader_view: typing.Optional[ListView] = None
        self.follower_view: typing.Optional[ListView] = None
        self.cluster_info_view: typing.Optional[ListView] = None


def get_system_role():
    return xconfig.WebConfig.cluster_node_role


def print_debug_info(*args):
    new_args = [dateutil.format_time(), "[system_sync]"]
    new_args += args
    print(*new_args)


def convert_dict_to_text(dict):
    return textutil.tojson(dict, format=True)



def get_system_role_manager():
    if SyncConfig.is_leader():
        return LeaderInstance
    else:
        return FollowerInstance

def get_system_sync_tab(tab_default="home"):
    tab = TabBox(tab_key="tab", tab_default=tab_default)
    tab.add_item(title="概览", value="home", href="/system/sync?p=home")
    tab.add_item(title="应用", value="app", href="/system/sync/app")
    tab.add_item(title="binlog", value="binlog", href="/system/sync/binlog")
    return tab

def get_system_sync_info_list():
    info_list = ListView()
    info_list.add_item(ListViewItem(text="当前节点类型", badge_info=xconfig.WebConfig.cluster_node_role, 
                                    css_class="list-item-black"))
    info_list.add_item(ListViewItem(text="当前节点ID", badge_info=xconfig.WebConfig.cluster_node_id, 
                                    css_class="list-item-black"))
    return info_list

def _config_btn(title: str, key: str, default: str) -> ActionButton:
    """「设置」按钮：点击后弹输入框（prompt_msg/prompt_value），由框架默认 onClick 提交 set_config"""
    return ActionButton(text="设置", css_class="btn btn-default",
                       url="/system/sync",
                       prompt_msg=title, prompt_value=textutil.safe_str(default),
                       data_params={"p": "set_config", "key": key})


def _confirm_btn(title: str, key: str, text: str, value: str = "true") -> ActionButton:
    """「重置 / 同步」按钮：点击后确认（confirm_msg），由框架默认 onClick 提交 set_config"""
    return ActionButton(text=text, css_class="btn btn-default",
                       url="/system/sync",
                       confirm_msg=title,
                       data_params={"p": "set_config", "key": key, "value": value})


def _build_cluster_info_view(kw: SystemSyncHomeModel) -> ListView:
    """集群信息列表（主从节点都展示）"""
    lv = ListView()

    title_item = ListViewItem()
    title_item.add_span("集群信息")
    title_item.extra.add(ActionButton(text="刷新", css_class="btn btn-default",
                                     url="/system/sync?p=refresh"))
    lv.add_item(title_item)

    if kw.ping_error:
        err_item = ListViewItem()
        err_item.add_span("错误信息")
        err_item.extra.add(TextSpan(text=textutil.safe_str(kw.ping_error), css_class="error"))
        lv.add_item(err_item)

    leader_item = ListViewItem()
    leader_item.add(TextTag(text="主节点", css_class="orange"))
    leader_item.add_span(textutil.safe_str(kw.leader_node_id))
    leader_item.add_link("(" + textutil.safe_str(kw.leader_url) + ")", textutil.safe_str(kw.leader_url))
    lv.add_item(leader_item)

    for info in kw.follower_list:
        item = ListViewItem()
        item.add(TextTag(text="从节点", css_class="info"))
        item.add_span(textutil.safe_str(info.node_id))
        item.add_link("(" + textutil.safe_str(info.http_url) + ")", textutil.safe_str(info.http_url))
        lv.add_item(item)

    return lv


def _build_leader_view(kw: SystemSyncHomeModel) -> ListView:
    """主节点视图：授权 token、白名单、文件索引数"""
    lv = ListView()

    item = ListViewItem()
    item.add_span("授权token")
    item.extra.add(_config_btn("更新token", "leader.token", textutil.safe_str(kw.leader_token)))
    lv.add_item(item)

    item = ListViewItem()
    item.add_span("子节点IP白名单")
    item.extra.add(_config_btn("更新白名单", "follower.whitelist", textutil.safe_str(kw.whitelist)))
    lv.add_item(item)

    item = ListViewItem()
    item.add_span("文件索引数")
    item.extra.add(TextSpan(text=textutil.safe_str(kw.fs_index_count)))
    lv.add_item(item)

    return lv


def _build_follower_view(kw: SystemSyncHomeModel) -> ListView:
    """从节点视图：主服务器配置、同步状态、文件/DB 同步进度、位点重置等"""
    lv = ListView()

    leader_host = textutil.safe_str(kw.leader_host)
    
    item = ListViewItem()
    item.add_span("主节点服务器: ")
    item.add_link(text=leader_host, href=leader_host)
    item.extra.add(_config_btn("设置主服务器", "leader.host", textutil.safe_str(kw.leader_host)))
    lv.add_item(item)

    item = ListViewItem()
    item.add_span("主服务器token")
    item.extra.add(_config_btn("设置主服务器token", "leader.token", textutil.safe_str(kw.leader_token)))
    lv.add_item(item)

    status_text = "开启" if kw.sync_status else "关闭"
    item = ListViewItem()
    item.add_span("同步状态")
    item.extra.add(TextSpan(text=f"当前: {status_text}"))
    item.extra.add(_confirm_btn("确认开启同步?", "sync_status", "开启同步", value="true"))
    item.extra.add(_confirm_btn("确认关闭同步?", "sync_status", "关闭同步", value="false"))
    lv.add_item(item)

    item = ListViewItem()
    item.add_span("文件索引同步")
    diff = int(kw.fs_max_index) - int(kw.fs_current_index)
    item.extra.add(TextSpan(text=f"{kw.fs_current_index} -> {kw.fs_max_index} (落后{diff})"))
    lv.add_item(item)

    item = ListViewItem()
    item.add_span("文件同步进度")
    item.extra.add(TextSpan(text=textutil.safe_str(kw.sync_process)))
    lv.add_item(item)

    item = ListViewItem()
    item.add_span("文件同步操作")
    item.extra.add(_confirm_btn("确认同步一次?", "trigger_fs_sync", "同步一次"))
    item.extra.add(_confirm_btn("确认重置文件同步位点?", "reset_fs_offset", "重置位点"))
    lv.add_item(item)

    if kw.fs_sync_failed_msg:
        item = ListViewItem()
        item.add_span("文件同步失败信息")
        item.extra.add(TextSpan(text=textutil.safe_str(kw.fs_sync_failed_msg)))
        lv.add_item(item)

    item = ListViewItem()
    item.add_span("DB同步状态")
    item.extra.add(TextSpan(text=textutil.safe_str(kw.follower_db_sync_state)))
    lv.add_item(item)

    
    if kw.follower_db_sync_state == "full":
        item = ListViewItem()
        item.add_span("全量同步当前key")
        item.extra.add(TextSpan(text=textutil.safe_str(kw.follower_db_last_key)))
        lv.add_item(item)

    item = ListViewItem()
    item.add_span("binlog位点")
    diff = int(kw.leader_binlog_seq) - int(kw.follower_binlog_seq)
    item.extra.add(TextSpan(
        text=f"{kw.follower_binlog_seq}->{kw.leader_binlog_seq} (落后{diff})"))
    lv.add_item(item)

    item = ListViewItem()
    item.add_span("binlog操作")
    item.extra.add(_confirm_btn("确认同步一次binlog?", "trigger_db_sync", "同步一次"))
    item.extra.add(_confirm_btn("确认重置当前位点?", "reset_offset", "重置位点"))
    
    lv.add_item(item)

    return lv


def get_leader_binlog_seq(role_manager: typing.Union[Leader, Follower]) -> int:
    leader_info = role_manager.get_leader_info()
    if leader_info == None:
        return -1
    return leader_info.binlog_last_seq


class SystemSyncHomePlugin(BaseListPlugin):
    """集群管理首页（概览），使用 webui 组件渲染，不再依赖 .html 模板"""

    title = T("集群管理")
    parent_link = LinkConfig.app_index
    show_category = False

    def handle_page(self):
        self.title = T("集群管理")

        role_manager = get_system_role_manager()

        try:
            role_manager.sync_for_home_page()
        except:
            xutils.print_exc()

        is_leader = SyncConfig.is_leader()

        kw = SystemSyncHomeModel()
        kw.node_role = get_system_role()
        kw.is_leader = is_leader
        kw.leader_host = ClusterConfigDao.get_leader_host()
        kw.leader_token = role_manager.get_leader_token()
        kw.leader_url = role_manager.get_leader_url()
        kw.leader_node_id = role_manager.get_leader_node_id()
        kw.leader_binlog_seq = get_leader_binlog_seq(role_manager)

        kw.follower_list = role_manager.get_follower_list()
        kw.ping_error = role_manager.get_ping_error()
        kw.fs_index_count = role_manager.get_fs_index_count()

        kw.whitelist = LeaderInstance.get_ip_whitelist()
        kw.sync_process = FollowerInstance.get_sync_process()
        kw.follower_binlog_seq = FollowerInstance.db_syncer.get_binlog_last_seq()
        kw.follower_db_sync_state = FollowerInstance.db_syncer.get_db_sync_state()
        kw.follower_db_last_key = FollowerInstance.db_syncer.get_db_last_key()
        kw.sync_status = SyncConfig.need_sync_db()

        if is_leader:
            kw.leader_view = _build_leader_view(kw)
        else:
            # 从节点
            kw.fs_max_index = FollowerInstance.fs_max_index
            kw.fs_current_index = FollowerInstance.get_fs_sync_last_id()
            kw.fs_sync_failed_msg = FollowerInstance.http_client.fs_sync_failed_msg
            kw.follower_view = _build_follower_view(kw)

        kw.cluster_info_view = _build_cluster_info_view(kw)

        # 依次渲染各区块（每个区块独立成卡片）
        self.add_component(Card().add(get_system_sync_tab()))
        self.add_component(Card().add(get_system_sync_info_list()))
        
        if kw.leader_view:
            self.add_component(Card().add(kw.leader_view))
        
        if kw.follower_view:
            self.add_component(Card().add(kw.follower_view))
        
        self.add_component(Card().add(kw.cluster_info_view))

        # 右侧管理导航
        self.show_aside = True
        self.aside_html = xtemplate.render("system/component/admin_nav.html").decode("utf-8")


class ConfigHandler:
    """处理同步相关的配置/操作（set_config），由框架默认 onClick 提交"""

    def execute(self):
        key = xutils.get_argument("key")
        value = xutils.get_argument("value")
        if not value:
            # 框架的 prompt 输入会放在 __input 字段
            value = xutils.get_argument("__input", "")

        if key == "leader.host":
            result = self.set_leader_host(value)
        elif key == "leader.token":
            result = self.set_leader_token(value)
        elif key == "reset_offset":
            result = self.reset_offset()
        elif key == "reset_fs_offset":
            result = self.reset_fs_offset()
        elif key == "trigger_sync":
            result = self.trigger_sync()
        elif key == "trigger_fs_sync":
            result = self.trigger_fs_sync()
        elif key == "trigger_db_sync":
            result = self.trigger_db_sync()
        elif key == "sync_status":
            result = self.set_sync_status(value)
        else:
            result = webutil.SuccessResult()

        if not result.success:
            return result

        # 框架 onClick 成功后会执行 commands，这里用 toast 反馈 + 刷新页面
        commands = webutil.CommandsResult()
        if result.message:
            commands.add_toast_command(result.message)
        commands.add_reload_command()
        return commands

    def reset_offset(self):
        FollowerInstance.reset_sync()
        return webutil.SuccessResult()

    def reset_fs_offset(self):
        FollowerInstance.reset_fs_offset()
        return webutil.SuccessResult()

    def trigger_sync(self):
        FollowerInstance.ping_leader()
        FollowerInstance.sync_files_from_leader()
        return webutil.SuccessResult()

    def trigger_fs_sync(self):
        FollowerInstance.ping_leader()
        FollowerInstance.sync_files_from_leader()
        return webutil.SuccessResult()

    def trigger_db_sync(self):
        """触发一次 DB/binlog 同步（增量 binlog 或全量，取决于当前同步状态）"""
        FollowerInstance.ping_leader()
        FollowerInstance.sync_db_from_leader()
        return webutil.SuccessResult()

    def set_leader_host(self, host):
        assert xutils.is_str(host), "host is not str"

        if not netutil.is_http_url(host):
            return webutil.FailedResult(code="400", message="无效的URL地址(%s)" % host)
        ClusterConfigDao.put_leader_host(host)
        SystemMetaEnum.leader_base_url.save_meta(host)
        return webutil.SuccessResult()

    def set_leader_token(self, token):
        ClusterConfigDao.put_leader_token(token)
        return webutil.SuccessResult()

    def set_sync_status(self, value):
        if value == None or value == "":
            return webutil.FailedResult(code="400", message="配置值为空")
        bool_value = str(value).lower() == "true"
        SyncConfig.set_need_sync_db(bool_value)
        SyncConfig.set_need_sync_files(bool_value)
        if bool_value:
            message = "同步已开启"
        else:
            message = "同步已关闭"
        return webutil.SuccessResult(message=message)


def get_leader_url():
    if get_system_role() == "leader":
        return "127.0.0.1"
    return ClusterConfigDao.get_leader_host()


class SyncHandler:

    def POST(self):
        return self.GET()

    def GET(self):
        p = xutils.get_argument_str("p", "")
        client_ip = webutil.get_client_ip()
        system_role = get_system_role()

        if p == "home" or p == "":
            return self.get_home_page()

        if p == "set_config":
            return self.do_set_config()

        if p == "refresh":
            return self.do_refresh()

        if p == "ping":
            return self.do_ping()

        if p == "get_detail":
            return self.get_detail()

        if p == "build_index":
            if not xconfig.get_global_config("system.build_fs_sync_index"):
                return webutil.FailedResult(code="403", message="文件同步索引未开启 [build_fs_sync_index]")

            return self.do_build_index()

        if p == "sync_files_from_leader":
            xauth.check_login("admin")
            return FollowerInstance.sync_files_from_leader()

        if p == "sync_db":
            xauth.check_login("admin")
            FollowerInstance.sync_db_from_leader()
            return webutil.SuccessResult()

        return LeaderHandler().handle_leader_action()
    
    @xauth.login_required("admin")
    def get_home_page(self):
        return SystemSyncHomePlugin().render()

    @xauth.login_required("admin")
    def do_set_config(self):
        handler = ConfigHandler()
        return handler.execute()

    @xauth.login_required("admin")
    def do_refresh(self):
        # 刷新按钮：仅重新加载页面（首页渲染时会重新拉取集群信息）
        commands = webutil.CommandsResult()
        commands.add_reload_command()
        return commands

    @xauth.login_required("admin")
    def get_detail(self):
        type = xutils.get_argument_str("type")
        key = xutils.get_argument_str("key")

        if type == "follower":
            role_manager = get_system_role_manager()
            info = role_manager.get_follower_info_by_url(key)
            result = webutil.SuccessResult(data=info)
            result.text=convert_dict_to_text(info)
            return result

        return webutil.FailedResult(code="500", message="未知的类型")

    def list_recent(self):
        result = Storage()
        result.code = "success"
        # TODO 读取filelist
        return result

    @xauth.login_required("admin")
    def do_build_index(self):
        manager = system_sync_indexer.FileSyncIndexManager()
        manager.build_full_index()
        return webutil.SuccessResult()

    def do_ping(self):
        if SyncConfig.is_leader():
            return webutil.SuccessResult(data=LeaderInstance.get_stat(""))
        data = FollowerInstance.ping_leader(force=True)
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
        leader_token = xutils.get_argument_str("leader_token")
        node_id = xutils.get_argument_str("node_id")
        port = xutils.get_argument_str("port")
        return LeaderInstance.refresh_token(leader_token=leader_token, node_id=node_id, port=port)


    def build_error(self, code="", message=""):
        error = webutil.FailedResult(code=code, message=message)
        status = "401 Unauthorized"
        headers = {"Content-Type": "application/json"}
        return web.HTTPError(status, headers, textutil.tojson(error))

    def check_token(self):
        if xauth.is_admin():
            return
        
        token = xutils.get_argument_str("token", "")
        if token == "":
            raise self.build_error(code="404", message="token为空")
        
        token_info = SystemSyncTokenDao.get_by_token(token)
        if token_info == None or token_info.is_expired():
            raise self.build_error(code="404", message="token无效或者过期")


    def list_files(self):
        """(主节点)读取文件列表"""
        last_id = xutils.get_argument_int("last_id", 0)
        result = webutil.SuccessResult()
        result.code = "success"
        result.req_last_id = last_id
        data = LeaderInstance.list_files(last_id=last_id)
        result.data = data
        return result

    def handle_leader_action(self):
        """主节点的提供的功能"""
        p = xutils.get_argument_str("p", "")
        if p == "get_token":
            return self.get_token()
        
        if p == "refresh_token":
            return self.refresh_token()
        
        # 没有token不允许继续
        self.check_token()

        if p == "get_stat":
            port = xutils.get_argument_str("port", "")
            return LeaderInstance.get_stat(port)

        if p == "list_files":
            return self.list_files()

        if p == "list_db":
            last_key = xutils.get_argument("last_key", "")
            limit = xutils.get_argument_int("limit", 20)
            data = LeaderInstance.list_db(last_key, limit)
            return webutil.SuccessResult(data=data)

        if p == "list_recent":
            return self.list_recent()

        return webutil.FailedResult(code="error", message="未知的操作")


class FollowerHandler(SyncHandler):

    @xauth.login_required("admin")
    def GET(self):
        p = xutils.get_argument_str("p", "")
        if p == "get_leader_stat":
            return FollowerInstance.get_leader_info()
        
        return webutil.FailedResult(code="400", message="unknown op")

@xmanager.listen("sys.init")
def init(ctx=None):
    LeaderInstance.get_leader_token()

@xmanager.listen("sync.step")
# @log_mem_info_deco("on_ping_leader")
def on_ping_leader(ctx=None):
    role = get_system_role()
    if role == "leader":
        return None
    
    # TODO 优化ping的时间

    try:        
        if FollowerInstance.is_token_active():
            return
            
        return FollowerInstance.ping_leader()
    except:
        xutils.print_exc()
        logging.error("ping_leader failed, wait 60 seconds...")
        time.sleep(60)


@xmanager.listen("sync.step")
# @log_mem_info_deco("on_sync_files_from_leader")
def on_sync_files_from_leader(ctx=None):
    if SyncConfig.is_leader():
        return None
    
    if not SyncConfig.need_sync_files():
        return None

    try:
        logging.debug("开始同步文件...")
        logging.debug("-" * 50)
        FollowerInstance.sync_files_from_leader()
    except:
        xutils.print_exc()
        logging.error("sync_files_from_leader failed, wait 60 seconds...")
        time.sleep(60)


@xmanager.listen("sync.step")
# @log_mem_info_deco("on_sync_db_from_leader")
def on_sync_db_from_leader(ctx=None):
    if SyncConfig.is_leader():
        return None
    
    if not SyncConfig.need_sync_db():
        return None

    try:
        logging.debug("开始同步数据库")
        logging.debug("-"*50)
        FollowerInstance.sync_db_from_leader()
    except:
        xutils.print_exc()
        logging.error("sync_db_from_leader failed, wait 60 seconds...")
        time.sleep(60)
    

xurls = (
    r"/system/sync", SyncHandler,
    r"/system/sync/leader", LeaderHandler,
    r"/system/sync/follower", FollowerHandler,
)
