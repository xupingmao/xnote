# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2018/05/25 10:52:11
# @modified 2018/08/11 11:18:04

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

if __name__ == '__main__':
    import doctest
    doctest.testmod()
