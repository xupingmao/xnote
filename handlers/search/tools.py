# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# 

"""Description here"""

import os
import sys
import xmanager
import xconfig
import xutils

SearchResult = xutils.SearchResult


def search(name):
    """查找`handlers/tools/`目录下的工具"""
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
    return files

# xmanager.register_search_func(r"(.*)", find_tools)