# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# Copyright (c) 2017
# 
"""Description here"""

import os
import sys
import re
import six
import xmanager
import xconfig
import xutils
import xauth
from xutils import text_contains, Storage

SearchResult = xutils.SearchResult
url_pattern = re.compile(r"(http|https)://[^ ]+")

def search_menu(files, name):
    for category in xconfig.MENU_LIST:
        if category.need_login and not xauth.has_login():
            continue
        if category.need_admin and not xauth.is_admin():
            continue
        for child in category.children:
            if text_contains(child.name, name):
                files.append(Storage(name = '菜单 - ' + child.name, url = child.url))

def search(ctx, name):
    # six.print_(xconfig)
    # 查找`handlers/tools/`目录下的工具
    if not ctx.search_tool:
        return
    tools_path = xconfig.TOOLS_DIR
    files = []
    basename_set = set()
    for filename in os.listdir(tools_path):
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
        f.url = "/tools/barcode?content=" + name
        files.append(f)
    search_menu(files, name)
    return files

