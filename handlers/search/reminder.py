# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# 

"""Description here"""

import os
import sys
import time

import xauth
import xutils
import xconfig
import xtables
import xmanager

SearchResult = xutils.SearchResult


def search(delay_mins, message):
    if not xauth.is_admin():
        return []
    db = xtables.get_schedule_table()
    url = "/tasks/alert/" + message

    millis = time.time() + int(delay_mins) * 60
    tm = time.localtime(millis)
    tm_wday = "no-repeat"
    tm_hour = tm.tm_hour
    tm_min  = tm.tm_min

    db.insert(url=url,
            ctime=xutils.format_time(),
            mtime=xutils.format_time(),
            tm_wday=tm_wday,
            tm_hour=tm_hour,
            tm_min=tm_min)

    xmanager.load_tasks()

    result = SearchResult()
    result.name = "提醒"
    result.raw = "提醒创建成功，将于%s提醒 %s" % (xutils.format_time(millis), message)
    return [result]

