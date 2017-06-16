# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/16
# 

"""Description here"""

import time
import xconfig
import xutils

def search(muteLast):
    if muteLast == "":
        last = 3

    xconfig.MUTE_END_TIME = time.time() + last * 60 * 60
    result = xutils.SearchResult()
    result.name = "命令 - 静音"
    result.raw  = "静音到 %s" % xutils.format_time(xconfig.MUTE_END_TIME)
    return [result]

def cancel():
    xconfig.MUTE_END_TIME = None
    result = xutils.SearchResult()
    result.name = "命令 - 取消静音"
    result.raw  = "已经取消静音"
    return [result]