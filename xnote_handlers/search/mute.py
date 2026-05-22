# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/16
# @modified 2018/07/01 01:00:44

"""Description here"""
import re
import time
import xutils
from xnote.core import xconfig
from xnote.core import xauth
from xnote.core import xmanager
from xnote.core.models import SearchContext

@xmanager.searchable(r"静音(.*)", description="静音搜索")
def search_mute(ctx: SearchContext):
    """静音搜索"""
    search_mute_common(ctx)

@xmanager.searchable(r"mute(.*)", description="静音搜索(英文)")
def search_mute_en(ctx: SearchContext):
    """静音搜索(英文)"""
    search_mute_common(ctx)
    
def search_mute_common(ctx: SearchContext):
    if not xauth.is_admin():
        return
    mute_last = ctx.groups[0] if ctx.groups else ""
    if mute_last == "":
        last = 3 * 60
    elif mute_last.endswith("小时"):
        pattern = r"(\d+)"
        match = re.match(pattern, mute_last).group(0)
        last = int(match) * 60
    else:
        last = 3 * 60

    xconfig.MUTE_END_TIME = time.time() + last * 60
    result = xutils.SearchResult()
    result.icon = "icon icon-terminal"
    result.name = "命令 - 静音"
    result.raw  = "静音到 %s" % xutils.format_time(xconfig.MUTE_END_TIME)
    ctx.tools.append(result)

@xmanager.searchable(r"取消静音", description="取消静音")
def cancel_mute(ctx: SearchContext):
    """取消静音"""
    if not xauth.is_admin():
        return
    xconfig.MUTE_END_TIME = None
    result = xutils.SearchResult()
    result.name = "命令 - 取消静音"
    result.raw  = "已经取消静音"
    ctx.tools.append(result)