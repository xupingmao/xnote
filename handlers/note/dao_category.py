# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-07-15 23:08:49
@LastEditors  : xupingmao
@LastEditTime : 2023-06-24 10:57:44
@FilePath     : /xnote/handlers/note/dao_category.py
@Description  : 描述
"""

from xutils import dateutil
from xutils import dbutil, cacheutil
import xutils

_db = dbutil.get_table("note_category")
_cat_cache = cacheutil.PrefixedCache("note_category:")

def upsert_category(user_name, category):
    assert user_name != None
    assert category != None
    assert category.user_name != None

    category.mtime = dateutil.format_datetime()

    if category._id == None:
        category.ctime = dateutil.format_datetime()

    result = _db.update_by_id(category.code, category, user_name=user_name)
    _cat_cache.delete(user_name)
    return result


def list_category(user_name):
    assert user_name != None
    assert isinstance(user_name, str)

    return []

def get_category_by_code(user_name, code):
    assert user_name != None
    assert code != None
    for item in list_category(user_name):
        if item.code == code:
            return item
    return None


def refresh_category_count(user_name, code):
    pass


xutils.register_func("note.list_category", list_category)
