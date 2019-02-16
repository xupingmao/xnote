# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# @modified 2019/02/16 01:29:52

"""Description here"""
import sys
import xmanager
import xutils
import xauth
from xtemplate import T

SearchResult = xutils.SearchResult

@xmanager.searchable(r"([a-zA-Z0-9\.]+)")
def search(ctx):
    """搜索Python文档"""
    if not xauth.is_admin():
        return
    name = ctx.groups[0]
    if name in sys.modules:
        item = SearchResult()
        item.name = T("Python Document") + " - %s" % name
        item.url = "/system/document?name=%s" % name
        item.content = ""
        ctx.tools.append(item)

