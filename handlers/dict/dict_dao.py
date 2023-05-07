# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-04-15 14:39:26
@LastEditors  : xupingmao
@LastEditTime : 2023-05-07 16:53:54
@FilePath     : /xnote/handlers/dict/dict_dao.py
@Description  : 描述
"""
import xtables
from xutils import Storage
from xutils import dateutil

class DictItem(Storage):

    def __init__(self):
        self.key = ""
        self.value = ""
        self.ctime = ""
        self.mtime = ""

def dict_to_obj(item):
    if item == None:
        return None
    result = DictItem()
    result.update(item)
    return result

def get_by_key(key):
    table = xtables.get_dict_table()
    item = table.select_first(where=dict(key=key))
    return dict_to_obj(item)

def get_by_id(id):
    table = xtables.get_dict_table()
    item = table.select_first(where=dict(id=id))
    return dict_to_obj(item)

def create(dict_item):
    table = xtables.get_dict_table()
    return table.insert(**dict_item)

def update(id, value):
    assert isinstance(id, int), "id必须为数字"
    table = xtables.get_dict_table()
    now = dateutil.format_datetime()
    return table.update(value = value, mtime = now, where = dict(id = id))

def delete(id):
    table = xtables.get_dict_table()
    return table.delete(where = dict(id = id))

