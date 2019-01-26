# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# @modified 2019/01/26 16:27:58

"""Description here"""
import sys
import xmanager
import xutils
import xauth

SearchResult = xutils.SearchResult

@xmanager.searchable(r"([a-zA-Z0-9\.]+)")
def search(ctx):
    """搜索Python文档"""
    if not xauth.is_admin():
        return
    name = ctx.groups[0]
    if name in sys.modules:
        item = SearchResult()
        item.name = "Python Document - %s" % name
        item.url = "/system/document?name=%s" % name
        item.content = ""
        ctx.tools.append(item)

