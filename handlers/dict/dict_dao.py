# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-04-15 14:39:26
@LastEditors  : xupingmao
@LastEditTime : 2023-12-24 21:37:56
@FilePath     : /xnote/handlers/dict/dict_dao.py
@Description  : 描述
"""
from xnote.core import xtables
from xnote.core import xconfig
from xutils import Storage
from xutils import dateutil, is_str

PAGE_SIZE = xconfig.PAGE_SIZE


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


def convert_dict_func(item):
    v = Storage()
    v.name = item.key
    v.value = item.value
    v.summary = item.value
    v.mtime = item.mtime
    v.ctime = item.ctime
    v.url = "/dict/update?id=%s" % item.id
    v.priority = 0
    v.show_next = True
    return v


def escape_sqlite_text(text):
    text = text.replace('/', '//')
    text = text.replace("'", '\'\'')
    text = text.replace('[', '/[')
    text = text.replace(']', '/]')
    text = text.replace('(', '/(')
    text = text.replace(')', '/)')
    return text

def search_escape(text):
    if not is_str(text):
        return text
    text = escape_sqlite_text(text)
    return "'%" + text + "%'"


def left_match_escape(text):
    return "'%s%%'" % escape_sqlite_text(text)


def search_dict(key, offset = 0, limit = None):
    if limit is None:
        limit = PAGE_SIZE
    db = xtables.get_dict_table()
    where_sql = "`key` LIKE %s" % left_match_escape(key)
    items = db.select(order="key", where = where_sql, limit=limit, offset=offset)
    items = list(map(convert_dict_func, items))
    count = db.count(where = where_sql)
    return items, count
