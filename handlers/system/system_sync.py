# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/11/07 12:38:32
# @modified 2021/11/07 19:37:05
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
import xauth
import xutils
import xconfig
import xtemplate
from xutils import webutil
from xutils import Storage


def get_system_role():
    return xconfig.get_global_config("system.node.role")

class SyncHandler:

    def GET(self):
        p = xutils.get_argument("p", "")
        token = xutils.get_argument("token", "")
        client_ip = webutil.get_client_ip()
        system_role = get_system_role()

        # print("client_ip", client_ip)
        # client_ip_whitelist = xconfig.get_global_config("client.ip.whitelist", type = list)
        # if client_ip not in client_ip_whitelist:
        #     return dict(code = "403", message = "无权访问")

        if p == "home":
            return self.get_home_page()

        if system_role != "leader":
            return dict(code = "500", message = "当前节点不是主节点")

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

    def get_home_page(self):
        kw = Storage()
        kw.node_role = get_system_role()
        return xtemplate.render("system/page/system_sync_admin.html", **kw)

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
        result = Storage()
        result.code = "success"
        result.timestamp = int(time.time())
        result.system_version = xconfig.get_global_config("system.version")

        return result


xurls = (
    r"/system/sync", SyncHandler
)