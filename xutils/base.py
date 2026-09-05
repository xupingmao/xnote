# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/11/28 23:23:13
# @modified 2022/04/16 22:47:23
import copy
import os
import traceback
import codecs
import json

string_types = (str,)


class MyStorage(dict):
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
    
    # 普通Python访问属性的顺序是 (不包含数据描述符的情况)
    # 1. obj.__dict__ 
    # 2. type(obj).__dict__
    # 3. __getattr__  # MyStorage覆盖的是这个方法
    # 如果新增 class 级别的属性会导致无法被 类属性覆盖

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
        if memo is None:
            memo = {}
        old_value = memo.get(id(self))
        if old_value != None:
            return old_value

        result = Storage()
        for key in self:
            value = self[key]
            result[key] = copy.deepcopy(value)
        return result
    
    def __repr__(self):     
        return f'<{self.__class__.__name__} {dict.__repr__(self)}>'

Storage = MyStorage

class XnoteException(Exception):
    def __init__(self, code="500", message=""):
        super(XnoteException, self).__init__(message)
        self.code = code
        self.message = message


def print_exc():
    """打印系统异常堆栈"""
    exc_info = traceback.format_exc()
    print(exc_info)
    return exc_info

def print_stacktrace():
    print_exc()

def is_str(s):
    return isinstance(s, string_types)


def makedirs(dirname):
    '''检查并创建目录(如果不存在不报错)'''
    if not os.path.exists(dirname):
        os.makedirs(dirname)
        return True
    return False


def decode_bytes(bytes: bytes):
    exc = None
    for charset in ("utf-8", "gbk", "mbcs", "latin_1"):
        try:
            return codecs.decode(bytes, charset)
        except Exception as e:
            exc = e
    if exc != None:
        raise exc
    raise Exception("can not decode bytes")

try_decode = decode_bytes


class BaseEnumItem:
    def __init__(self, name="", value=""):
        self.name = name # enum name
        self.value = value # enum value
        self._int_cache = None
    
    @property
    def int_value(self):
        if self._int_cache is not None:
            return self._int_cache
        
        self._int_cache = int(self.value)
        return self._int_cache

EnumItem = BaseEnumItem

class BaseEnum:
    """枚举的基类,和python自带的不同,允许动态新增枚举值"""
    @classmethod
    def enums(cls):
        result = [] # type: list[BaseEnumItem]
        for key in cls.__dict__:
            item = getattr(cls, key, None)
            if isinstance(item, BaseEnumItem):
                result.append(item)
        return result
    
    @classmethod
    def get_by_value(cls, value=""):
        for item in cls.enums():
            if item.value == value:
                return item
        return None
    
    @classmethod
    def get_name_by_value(cls, value=""):
        for item in cls.enums():
            if item.value == value:
                return item.name
        return ""
    

class BaseDataRecord(Storage):
    _ignore_save_fields = []

    def handle_from_dict(self):
        pass
    
    @classmethod
    def from_dict(cls, dict_value):
        result = cls()
        result.update(dict_value)
        result.handle_from_dict()
        return result
    
    @classmethod
    def from_dict_or_None(cls, dict_value):
        if dict_value is None:
            return None
        return cls.from_dict(dict_value)
    
    @classmethod
    def from_json(cls, json_value: str):
        if json_value == "":
            return None
        dict_value = json.loads(json_value)
        return cls.from_dict(dict_value)

    @classmethod    
    def from_dict_list(cls, dict_list):
        return [cls.from_dict(item) for item in dict_list]

    def to_save_dict(self):
        """
        转换成字典用于保存操作(insert or update)
        """
        result = dict(**self)
        for name in self._ignore_save_fields:
            result.pop(name, None)
        return result
        


