# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# Copyright (c) 2017
# @modified 2019/01/26 16:41:07
"""Description here"""

import os
import sys
import re
import socket
import six
import xmanager
import xconfig
import xutils
import xauth
from xutils import text_contains, Storage, u

SearchResult = xutils.SearchResult
url_pattern = re.compile(r"(http|https)://[^ ]+")

def search_menu(files, name):
    for category in xconfig.MENU_LIST:
        if category.need_login and not xauth.has_login():
            continue
        if category.need_admin and not xauth.is_admin():
            continue
        for child in category.children:
            if text_contains(u(child.name), u(name)):
                files.append(Storage(name = '菜单 - ' + child.name, url = child.url))

@xmanager.searchable(r"([^ ]+)")
def search(ctx):
    # six.print_(xconfig)
    # 查找`handlers/tools/`目录下的工具
    if not ctx.search_tool:
        return
    name = ctx.key
    tools_path = xconfig.TOOLS_DIR
    files = []
    basename_set = set()
    for filename in os.listdir(tools_path):
        if filename[0] == '_':
            continue
        _filename, ext = os.path.splitext(filename)
        if ext in (".html", ".py"):
            basename_set.add(_filename)

    for filename in basename_set:
        if name in filename:
            f = SearchResult()
            f.name = "工具 - " + filename
            f.url = "/tools/" + filename
            f.content = filename
            files.append(f)

    if url_pattern.match(name):
        f = SearchResult()
        f.name = "分析网页资源 - " + name
        f.url = "/tools/html_importer?url=" + name
        files.append(f)

        f = SearchResult()
        f.name = "二维码"
        f.url = "/tools/qrcode?content=" + name
        files.append(f)
    search_menu(files, name)
    
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
    blacklist = xconfig.get("IP_BLACK_LIST")
    ip_list = get_ip_list(blacklist)
    return ip_list[0]

@xmanager.searchable('addr')
def show_addr_qrcode(ctx):
    r = SearchResult()
    addr = "http://" + get_server_ip() + ":" + str(xconfig.PORT)
    r.url = addr
    r.name = '地址 - %s' % addr
    r.html = '''<script type="text/javascript" src="/static/lib/jquery.qrcode/jquery.qrcode.min.js"></script>
    <div id='qrcode'></div>
    <script>$("#qrcode").qrcode('%s');</script>
    ''' % addr
    ctx.tools.append(r)

