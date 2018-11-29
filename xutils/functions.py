# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/05/25 10:52:11
# @modified 2018/11/29 23:24:24
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

    def __init__(self, maxsize=1000):
        if not isinstance(maxsize, int):
            raise TypeError("maxsize must be int")
        self.maxsize = maxsize
        self.data = deque()

    def _insert(self, **value):
        self.data.append(value)
        if len(self.data) > self.maxsize:
            self.data.popleft()
        return value

    def insert(self, **value):
        return self._insert(**value)

    def _update(self, columns, func):
        '''update rows
        :arg dict columns: updated values
        :arg func func: filter function
        '''
        rows = self.list(0,-1,func)
        for row in rows:
            row.update(columns)
        return len(rows)

    def update(self, columns, func):
        return self._update(columns, func)

    def add(self, name, extinfo=None):
        self.data.append(self.new_value(name, extinfo))
        if len(self.data) > self.maxsize:
            self.data.popleft()

    def list(self, offset, limit=-1, func=None):
        '''find list from data

        :arg int offset: offset from 0
        :arg int limit:
        :arg func func:
        '''
        items = self.data
        result = []
        if items is None:
            return result
        index = 0
        for value in items:
            if func is None:
                index += 1
            elif func(value):
                index += 1
            if index > offset:
                result.append(value)
            if limit >= 0 and len(result) >= limit:
                break
        return result

    def first(self, func=None):
        result = self.list(0,1,func)
        if len(result) == 0:
            return None
        return result[0]

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

    def new_value(self, name, extinfo):
        return HistoryItem(name, extinfo)

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

def listremove(list, obj):
    if list is None:
        return
    while obj in list:
        list.remove(obj)

def dictsort(dictionary, key='value'):
    if key == 'value':
        return sorted(dictionary.items(), key = lambda item: item[1])
    return sorted(dictionary.items(), key = lambda item: item[0])

if __name__ == '__main__':
    import doctest
    doctest.testmod()
