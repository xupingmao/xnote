# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/11/28 23:23:13
# @modified 2020/11/28 23:24:04


class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`. (This class is modified from web.py)
    
        >>> o = storage(a=1)
        >>> o.a
        1
        >>> o['a']
        1
        >>> o.a = 2
        >>> o['a']
        2
        >>> o.noSuchKey
        None
    """
    def __init__(self, **kw):
        # default_value会导致items等函数出问题
        # self.default_value = default_value
        super(Storage, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as k:
            return None
    
    def __setattr__(self, key, value): 
        self[key] = value
    
    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError as k:
            raise AttributeError(k)

    def __deepcopy__(self, memo):
        return Storage(**self)
    
    def __repr__(self):     
        return '<MyStorage ' + dict.__repr__(self) + '>'

