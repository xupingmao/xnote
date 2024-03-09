# encoding=utf-8
# @author xupingmao
# @since 2016/12/09
# @modified 2022/02/05 21:54:58

"""处理时间的工具类

==========
格式化的参数
==========

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

=======
tm结构体
=======
tm_year  实际的年份
tm_mon   月份（从一月开始，0代表一月） - 取值区间为[0,11]
tm_mday  一个月中的日期 - 取值区间为[1,31]
tm_wday  星期 – 取值区间为[0,6]，其中0代表星期天，1代表星期一，以此类推
tm_yday  从每年的1月1日开始的天数 – 取值区间为[0,365]，其中0代表1月1日，1代表1月2日，以此类推


"""

import time
import math
import datetime

SECONDS_PER_DAY = 3600 * 24
DEFAULT_FORMAT = '%Y-%m-%d %H:%M:%S'
FORMAT = DEFAULT_FORMAT
DATE_FORMAT = "%Y-%m-%d"

WDAY_DICT = {
    "*": u"每天",
    "1": u"周一",
    "2": u"周二",
    "3": u"周三",
    "4": u"周四",
    "5": u"周五",
    "6": u"周六",
    "7": u"周日"
}

class DateClass:

    def __init__(self):
        self.year = 0
        self.month = 0
        self.day = 0
        self.wday = 0 # week day

    def __repr__(self):
        return "(%r,%r,%r)" % (self.year, self.month, self.day)


def is_str(s):
    return isinstance(s, str)

def before(days=None, month=None, format=False):
    if days is not None:
        fasttime = time.time() - days * SECONDS_PER_DAY
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


def format_datetime(value=None, format='%Y-%m-%d %H:%M:%S'):
    """格式化日期时间
    >>> format_datetime(0)
    '1970-01-01 08:00:00'
    """
    if value == None:
        return time.strftime(format)
    elif isinstance(value, datetime.datetime):
        return value.strftime(format)
    else:
        st = time.localtime(value)
        return time.strftime(format, st)

def format_time(seconds = None):
    return format_datetime(seconds)

def format_time_only(seconds=None):
    """只格式化时间 TODO 时区问题
    >>> format_time_only(0)
    '08:00:00'
    """
    if seconds == None:
        return time.strftime('%H:%M:%S')
    else:
        st = time.localtime(seconds)
        return time.strftime('%H:%M:%S', st)

def format_weekday(date_str, fmt = "") -> str:
    if fmt == "":
        fmt = "%Y-%m-%d"
    
    tm = time.strptime(date_str, fmt)
    wday = str(tm.tm_wday + 1)
    return WDAY_DICT.get(wday) or ""

format_wday = format_weekday

def datetime_to_weekday(datetime_obj):
    """把datetime转换成星期"""
    if datetime_obj is None:
        return ""
    if isinstance(datetime_obj, datetime.datetime):
        weekday = str(datetime_obj.weekday()+1)
        return WDAY_DICT.get(weekday, "")
    if isinstance(datetime_obj, str):
        parts = datetime_obj.split()
        if len(parts) == 0:
            return ""
        date_str = parts[0]
        return format_weekday(date_str)
    raise Exception("unsupported type: %r" % type(datetime_obj))

def format_date(seconds=None, fmt = None):
    """格式化日期
    >>> format_date("2020-01-01 00:00:00", "/")
    '2020/02/01'
    >>> format_date(1000)
    '1970-01-01'
    >>> format_date(1000, "/")
    '1970/01/01'
    """
    arg_fmt = fmt
    if fmt is None:
        fmt = "%Y-%m-%d"
    if arg_fmt == "/":
        fmt = "%Y/%m/%d"
    if seconds is None:
        return time.strftime(fmt)
    elif isinstance(seconds, datetime.datetime):
        return seconds.strftime(fmt)
    elif is_str(seconds):
        date_str = seconds.split(" ")[0]
        if arg_fmt == "/":
            date_str = date_str.replace("-", "/")
        return date_str
    else:
        st = time.localtime(seconds)
        return time.strftime(fmt, st)

def format_mmdd(seconds=None):
    """格式化月/日
    >>> format_mmdd(0)
    '01/01'
    >>> format_mmdd("2020-12-02")
    '12/02'
    """
    if isinstance(seconds, str):
        date_part = seconds.split(" ")[0]
        date_part = date_part.replace("-", "/")
        parts = date_part.split("/")
        if len(parts) != 3:
            return date_part
        return "%s/%s" % (parts[-2], parts[-1])
    else:
        return format_date(seconds, "%m/%d")

def format_millis(mills):
    return format_time(mills / 1000)

def parse_date_to_timestamp(date_str):
    st = time.strptime(date_str, DATE_FORMAT)
    return time.mktime(st)

def parse_date_to_struct(date_str=""):
    return time.strptime(date_str, DATE_FORMAT)

def parse_date_to_object(date_str):
    """解析日期结构
    @param {string} date_str 日期的格式

        >>> parse_date_to_object("2020-01")
        (2020,1,None)
        >>> parse_date_to_object("2020")
        (2020,None,None)
        >>> parse_date_to_object("2020-01-01")
        (2020,1,1)
    """
    assert date_str != None
    assert is_str(date_str)
    parts = date_str.split("-")
    
    date_object = DateClass()

    def _parse_int(value):
        try:
            return int(value)
        except:
            raise Exception("parse_date: invalid date str %r" % date_str)

    if len(parts) == 0:
        raise Exception("parse_date: invalid date str %r" % date_str)
        
    if len(parts) >= 1:
        date_object.year = _parse_int(parts[0])

    if len(parts) >= 2:
        date_object.month = _parse_int(parts[1])

    if len(parts) >= 3:
        date_object.day = _parse_int(parts[2])

    return date_object


def parse_datetime(date = "", fmt = DEFAULT_FORMAT):
    """解析时间字符串为unix时间戳
    :param {string} date: 时间
    :param {string} fmt: 时间的格式
    :return {int}: 时间戳，单位是秒
    """
    if date == "":
        return int(time.time())
    if isinstance(date, datetime.datetime):
        return date.timestamp()
    st = time.strptime(date, fmt)
    return time.mktime(st)

parse_time = parse_datetime

def get_seconds(date = "", fmt = DEFAULT_FORMAT):
    return parse_datetime(date, fmt)

def get_current_year():
    """获取当前年份"""
    tm = time.localtime()
    return tm.tm_year

def get_current_month():
    """获取当前月份"""
    tm = time.localtime()
    return tm.tm_mon

def get_current_mday():
    """返回今天在当前月份的日子"""
    tm = time.localtime()
    return tm.tm_mday

def current_wday() -> str:
    tm = time.localtime()
    wday = str(tm.tm_wday + 1)
    return WDAY_DICT.get(wday) or ""

def convert_date_to_wday(date_str):
    return format_wday(date_str)

def date_str_add(date_str="1970-01-01", years=0, months=0, days=0):
    tm = parse_date_to_struct(date_str)
    year, month, day = date_add(tm, years=years, months=months, days=days)
    return datetime.datetime(year, month, day).strftime(DATE_FORMAT)

def date_add(tm, years = 0, months = 0, days = 0):
    """date计算"""
    if tm is None:
        tm = time.localtime()
    else:
        assert isinstance(tm, time.struct_time)
    
    year  = tm.tm_year
    month = tm.tm_mon
    day   = tm.tm_mday
    if years != 0:
        year += years
    if months != 0:
        assert months > -12
        if months < 0:
            year -= 1
            months += 12
        month += months
        year += math.floor((month - 1.0) / 12)
        month = (month - 1) % 12 + 1
    if days != 0:
        date_obj = datetime.datetime(year=year, month=month, day=day)
        date_obj += datetime.timedelta(days=days)
        return date_obj.year, date_obj.month, date_obj.day
    return int(year), month, day

def is_leap_year(year):
    return ((year % 4 == 0) and (year % 100 != 0)) or (year % 400 == 0)

def get_days_of_month(year, month):
    """获取指定月份的天数 (get days of a month)
        >>> get_days_of_month(2000, 2)
        29
        >>> get_days_of_month(2001, 2)
        28
        >>> get_days_of_month(2002, 1)
        31
        >>> get_days_of_month(1900, 2)
        28
    """
    days = [ 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 ]
    if 2 == month:
        if is_leap_year(year):
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
    if day is not None and day != tm.tm_mday:
        return False
    if wday is not None and wday != tm.tm_wday:
        return False
    return True

def get_today():
    return format_date()

