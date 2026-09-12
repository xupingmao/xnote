# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# Copyright (c) 2017
# @modified 2021/07/25 10:11:58
"""Description here"""

import os
import sys
import re
import socket
import xutils

from xnote.core import xmanager
from xnote.core import xconfig
from xnote.core import xauth
from xnote.core.models import SearchContext
from xutils import text_contains, Storage, u
from xnote.plugin import TabBox

SearchResult = xutils.SearchResult
url_pattern = re.compile(r"(http|https)://[^ ]+")

@xmanager.searchable(r"([^ ]+)")
def search(ctx: SearchContext):
    # 查找`handlers/tools/`目录下的工具
    if not ctx.search_tool:
        return
    server_home = xconfig.WebConfig.server_home
    name = ctx.key
    files = []

    if url_pattern.match(name):
        f = SearchResult()
        f.show_move = False
        f.name = "导入笔记 - " + name
        f.url = f"{server_home}/note/html_importer?url=" + xutils.encode_uri_component(name)
        files.append(f)

        f = SearchResult()
        f.show_move = False
        f.name = "二维码"
        f.url = f"{server_home}/tools/qrcode?content={name}"
        files.append(f)

    ctx.tools += files

@xutils.cache(key="ip_list", expire=3600)
def get_ip_list(blacklist = []):
    """
    获取本地IP，加上缓存是因为失败的情况下调用非常缓慢
    """
    try:
        hostname = socket.gethostname()
        localIp = socket.gethostbyname(hostname)
        print("localIP:%s" % localIp)
        name, aliaslist, ipList = socket.gethostbyname_ex(hostname)
        ip_list = []
        for ip in ipList:
            if ip in blacklist:
                continue
            if ip != localIp:
               print("external IP:%s"%ip)
            ip_list.append(ip)
    except Exception as e:
        xutils.print_exc()
        ip_list = ["localhost"]

    return ip_list

def get_server_ip():
    ip_list = get_ip_list()
    return ip_list[0]

@xmanager.searchable('addr')
def show_addr_qrcode(ctx: SearchContext):
    index = 0
    ctx.init_html += """<script type="text/javascript" src="/_static/lib/jquery.qrcode/jquery.qrcode.min.js"></script>"""
    
    for server_ip in get_ip_list():
        index += 1
        r = SearchResult()
        r.show_move = False
        r.icon = "icon-barcode"
        addr = "http://" + server_ip + ":" + str(xconfig.PORT)
        r.url = addr
        r.name = f'[地址] {addr}'
        r.html = f"""<div id='qrcode-{index}'></div>
        <script>$("#qrcode-{index}").qrcode('{addr}');</script>
        <div class="top-offset-1">相关工具: <a href="{xconfig.WebConfig.server_home}/tools/qrcode">二维码生成器</a></div>"""
        ctx.commands.append(r)

    