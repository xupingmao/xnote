# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/16
# @modified 2018/07/01 01:00:44

"""Description here"""
import re
import time
import xconfig
import xutils
import xauth

def search(ctx, mute_last):
    if not xauth.is_admin():
        return
    if mute_last == "":
        last = 3 * 60
    elif mute_last.endswith("小时"):
        pattern = r"(\d+)"
        match = re.match(pattern, mute_last).group(0)
        last = int(match) * 60

    xconfig.MUTE_END_TIME = time.time() + last * 60
    result = xutils.SearchResult()
    result.name = "命令 - 静音"
    result.raw  = "静音到 %s" % xutils.format_time(xconfig.MUTE_END_TIME)
    return [result]

def cancel(ctx, *args):
    if not xauth.is_admin():
        return
    xconfig.MUTE_END_TIME = None
    result = xutils.SearchResult()
    result.name = "命令 - 取消静音"
    result.raw  = "已经取消静音"
    return [result]