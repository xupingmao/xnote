# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# 

"""Description here"""

import sys
import xmanager
import xutils
import xauth

SearchResult = xutils.SearchResult

def search(name):
    """搜索Python文档"""
    if not xauth.is_admin():
        return
    if name in sys.modules:
        item = SearchResult()
        item.name = "Python Document - %s" % name
        item.url = "/system/document?name=%s" % name
        item.content = ""
        return [item]
    return []

# xmanager.register_search_func(r"(.*)", find_py_docs)