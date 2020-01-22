# encoding=utf-8
# @author xupingmao
# @since 2016/12/09
# @modified 2020/01/22 12:33:52
import time
import os
import math
from .imports import is_str
"""处理时间的工具类
Commonly used format codes:

%Y  Year with century as a decimal number.
%m  Month as a decimal number [01,12].
%d  Day of the month as a decimal number [01,31].
%H  Hour (24-hour clock) as a decimal number [00,23].
%M  Minute as a decimal number [00,59].
%S  Second as a decimal number [00,61].
%z  Time zone offset from UTC.
%a  Locale's abbreviated weekday name.
%A  Locale's full weekday name.
%b  Locale's abbreviated month name.
%B  Locale's full month name.
%c  Locale's appropriate date and time representation.
%I  Hour (12-hour clock) as a decimal number [01,12].
%p  Locale's equivalent of either AM or PM.
"""


_DAY = 3600 * 24
FORMAT = '%Y-%m-%d %H:%M:%S'
wday_dict = {
    "*": u"每天",
    "1": u"周一",
    "2": u"周二",
    "3": u"周三",
    "4": u"周四",
    "5": u"周五",
    "6": u"周六",
    "7": u"周日"
}

def before(days=None, month=None, format=False):
    if days is not None:
        fasttime = time.time() - days * _DAY
        if format:
            return format_time(fasttime)
        return fasttime
    return None

def days_before(days, format=False):
    seconds = time.time()
    seconds -= days * 3600 * 24
    if format:
        return format_time(seconds)
    return time.localtime(seconds)


def format_datetime(seconds=None):
    if seconds == None:
        return time.strftime('%Y-%m-%d %H:%M:%S')
    else:
        st = time.localtime(seconds)
        return time.strftime('%Y-%m-%d %H:%M:%S', st)

format_time = format_datetime


def format_time_only(seconds=None):
    if seconds == None:
        return time.strftime('%H:%M:%S')
    else:
        st = time.localtime(seconds)
        return time.strftime('%H:%M:%S', st)


def format_date(seconds=None, fmt = None):
    if fmt is None:
        fmt = "%Y-%m-%d"
    if fmt == "/":
        fmt = "%Y/%m/%d"
    if seconds is None:
        return time.strftime(fmt)
    elif is_str(seconds):
        date_str = seconds.split(" ")[0]
        return date_str
    else:
        st = time.localtime(seconds)
        return time.strftime(fmt, st)

def format_mmdd(seconds=None):
    if is_str(seconds):
        date_part = seconds.split(" ")[0]
        date_part = date_part.replace("-", "/")
        parts = date_part.split("/")
        if len(parts) < 2:
            return date_part
        return "%s/%s" % (parts[-2], parts[-1])
    else:
        return format_date(seconds, "%m/%d")

def format_millis(mills):
    return format_time(mills / 1000)


def parse_time(date = None, fmt = None):
    if date is None:
        return int(time.time())
    if fmt is None:
        fmt = '%Y-%m-%d %H:%M:%S'
    st = time.strptime(date, fmt)
    return time.mktime(st)

get_seconds = parse_time

def get_current_year():
    return time.strftime("%Y")

def current_wday():
    tm = time.localtime()
    wday = str(tm.tm_wday + 1)
    return wday_dict.get(wday)

def date_add(tm, years = 0, months = 0, days = 0):
    if tm is None:
        tm = time.localtime()
    year  = tm.tm_year
    month = tm.tm_mon
    day   = tm.tm_mday
    if years != 0:
        year += years
    if months != 0:
        month += months
        year += math.floor((month - 1.0) / 12)
        month = (month - 1) % 12 + 1
    # TODO days
    return int(year), month, day

def get_days_of_month(y, month):
    """get days of a month
        >>> get_days_of_month(2000, 2)
        29
        >>> get_days_of_month(2001, 2)
        28
        >>> get_days_of_month(2002, 1)
        31
    """
    days = [ 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 ]
    if 2 == month:
        if (0 == y % 4) and (0 != y % 100) or (0 == y % 400):
            d = 29
        else:
            d = 28
    else:
        d = days[month-1]
    return d;

class Timer:

    def __init__(self, name = "[unknown]"):
        self.name = name

    def start(self):
        self.start_time = time.time()

    def stop(self):
        self.stop_time = time.time()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        import xutils
        self.stop()
        xutils.log("%s cost time: %s" % (self.name, self.cost()))


    def cost(self):
        return "%s ms" % int((self.stop_time - self.start_time) * 1000)

    def cost_millis(self):
        return int((self.stop_time - self.start_time) * 1000)


def match_time(year = None, month = None, day = None, wday = None, tm = None):
    if tm is None:
        tm = time.localtime()
    if year is not None and year != tm.tm_year:
        return False
    if month is not None and month != tm.tm_mon:
        return False
    if day is not None and day != tm.tm_day:
        return False
    if wday is not None and wday != tm.tm_wday:
        return False
    return True
