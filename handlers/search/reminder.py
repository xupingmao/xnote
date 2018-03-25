# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# 

"""Description here"""

import os
import sys
import time
import re
import xauth
import xutils
import xconfig
import xtables
import xmanager

SearchResult = xutils.SearchResult

num_dict = {
    '一' : '1',
    '二' : '2',
    '三' : '3',
    '四' : '4',
    '五' : '5',
    '六' : '6',
    '七' : '7',
    '八' : '8',
    '九' : '9',
    '零' : '0',
    '十' : '',
    '百' : '',
    '千' : '',
    '万' : '',
    '亿' : ''
}


def add_alarm(tm_hour, tm_min, message):
    db = xtables.get_schedule_table()
    url = "/api/alarm"
    tm_wday = "no-repeat"
    name = "[提醒] %s" % message

    db.insert(name=name,
            url=url,
            message=message,
            ctime=xutils.format_time(),
            mtime=xutils.format_time(),
            tm_wday=tm_wday,
            tm_hour=tm_hour,
            tm_min=tm_min)
    xmanager.load_tasks()

def parse_int(value):
    # ?万?千?百?十
    # vlist = [num_dict.get(v, v) for v in value]
    # value = ''.join(vlist)
    return int(value)

def search(ctx, delay_mins_str, message):
    if not xauth.is_admin():
        return []

    delay_mins = parse_int(delay_mins_str)
    millis = time.time() + int(delay_mins) * 60
    tm = time.localtime(millis)
    tm_hour = tm.tm_hour
    tm_min  = tm.tm_min
    add_alarm(tm_hour, tm_min, message)

    result = SearchResult()
    result.name = "提醒"
    result.raw = "提醒创建成功，将于%s点%s分提醒 %s" % (tm_hour, tm_min, message)
    result.url = "/system/crontab"
    xutils.say(result.raw)
    return [result]

time_pattern = re.compile(r"([0-9])点(半?)([0-9]*)")

def by_time(ctx, period, time_str, message):
    if not xauth.is_admin():
        return None
    print(period, time_str, message)
    v = time_pattern.findall(time_str)
    if len(v) > 0:
        tm_hour, tm_min, tm_min2 = v[0]
        tm_hour = int(tm_hour)
        if period == "下午":
            tm_hour += 12
        if tm_min == "半":
            tm_min = 30
        if tm_min2 != None and tm_min2.isdigit():
            tm_min = int(tm_min2)
        if tm_min == "":
            tm_min = 0
        add_alarm(tm_hour, tm_min, message)
        out = "提醒创建成功，将于%s点%s分提醒%s" % (tm_hour, tm_min, message)
        xutils.say(out)
        return [SearchResult("提醒", "/system/crontab", out)]

def by_date(ctx, date_str, message):
    if not xauth.is_admin():
        return None
    print(date_str, message)
