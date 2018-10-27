# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/05/25 10:52:11
# @modified 2018/10/27 18:25:00
import xconfig
from xconfig import Storage
from collections import deque
from .dateutil import format_time

class Counter:

    def __init__(self, sorted=False):
        self.dict = {}

    def incr(self, key):
        if key in self.dict:
            self.dict[key] += 1
        else:
            self.dict[key] = 1
    
    def decr(self, key):
        if key in self.dict:
            self.dict[key] -= 1
        else:
            self.dict[key] = -1
            
    def __iter__(self):
        return list(self.dict.keys())
            
    def __str__(self):
        return str(self.dict)


class ListProcessor:

    def __init__(self, data):
        self.list = data

    def select(self, columns):
        self.columns = columns
        return self

    def where(self, filter):
        self.filter = filter
        return self

    def orderby(self, orderby):
        self.orderby = orderby
        return self

    def limit(self, offset=0, limit=10):
        return self

    def fetchall(self):
        # process data 
        pass


def xfilter(func, iterables, offset=0, limit=-1):
    """filter增强，支持offset，limit
    >>> list(xfilter(lambda x:x>1, [1,2,3,4]))
    [2, 3, 4]
    >>> list(xfilter(lambda x:x>1, [1,2,3,4], 0, 1))
    [2]
    """
    current = 0
    total = 0
    if iterables:
        for item in iterables:
            if func(item):
                if current >= offset:
                    yield item
                    total += 1
                if limit > 0 and total >= limit:
                    break
                current += 1

class HistoryItem:

    def __init__(self, name, extinfo):
        self.name = name
        self.extinfo = extinfo
        self.time = format_time()
        self.count = 1

    def __str__(self):
        return "%s - [%s](%s) %s" % (self.time, self.name, self.extinfo, self.count)

class MemTable:
    """内存表, Queue无法遍历, deque是基于数组的，线程安全的"""

    def __init__(self, maxsize):
        self.maxsize = maxsize
        self.data = deque()

    def new_value(self, name, extinfo):
        return HistoryItem(name, extinfo)

    def _insert(self, **value):
        self.data.append(value)
        if len(self.data) > self.maxsize:
            self.data.popleft()

    def insert(self, **value):
        return self._insert(value)

    def update(self, value, where=None):
        self.data.append(self.new_value(name,extinfo))
        if len(self.data) > self.maxsize:
            self.data.popleft()

    def add(self, name, extinfo=None):
        self.data.append(self.new_value(name, extinfo))
        if len(self.data) > self.maxsize:
            self.data.popleft()

    def put(self, name, extinfo=None):
        """put操作会检查历史中有没有相同的项目，如果有的话更新时间和count值，并且移动到队列尾部"""
        found = None
        for value in self.data:
            if value.name == name and value.extinfo == extinfo:
                found = value
                self.data.remove(value)
                break
        if found == None:
            found = self.new_value(name, extinfo)
        found.count += 1
        found.time = format_time()
        self.data.append(found)

    def list(self, offset, limit=20):
        items = self.data
        result = []
        if items is None:
            return result
        for index, value in enumerate(items):
            if limit >= 0 and len(result) >= limit:
                break
            if index >= offset:
                result.append(value)
        return result

    def query_list(self, func, limit=-1):
        items = self.data
        result = []
        if items is None:
            return result
        index = 0
        while index < len(items):
            value = items[index]
            if func(value):
                result.append(value)
            if limit >= 0 and len(result) >= limit:
                break
            index += 1
        return result

    def recent(self, limit=20, func=None):
        items = self.data
        result = []
        if items is None:
            return result
        index = len(items) - 1
        while index >= 0 and limit > 0:
            value = items[index]
            if func is None:
                result.append(value)
            elif func(value):
                    result.append(value)
            index -= 1
            limit -= 1
        return result

    def clear(self, type):
        self.data.clear()

    def get(self):
        return self.data.pop()

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        return iter(self.data)

    def __str__(self):
        return str(self.data)

    @staticmethod
    def get_items(name):
        return History.items.get(name, [])

class History(MemTable):

    def __init__(self, type, maxsize):
        self.type = type
        MemTable.__init__(self, maxsize=maxsize)

    def add(self, key, rt=-1):
        import xauth
        self._insert(type = self.type,
            ctime = format_time(), 
            user = xauth.get_current_name(), 
            key = key, 
            rt = rt)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
