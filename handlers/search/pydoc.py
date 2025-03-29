# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# @modified 2019/02/16 01:29:52

"""Description here"""
import sys
import xutils

from xnote.core import xmanager
from xnote.core import xauth
from xnote.core.xtemplate import T
from xnote.core.models import SearchResult, SearchContext

@xmanager.searchable(r"([a-zA-Z0-9\.]+)")
def search(ctx: SearchContext):
    """搜索Python文档"""
    if not xauth.is_admin():
        return
    name = ctx.groups[0]
    if name in sys.modules:
        prefix = T("Python Document")
        item = SearchResult()
        item.name = f"【{prefix}】{name}"
        item.url = f"/system/document?name={name}"
        item.content = ""
        item.icon = "fa fa-file-text-o"
        ctx.tools.append(item)

