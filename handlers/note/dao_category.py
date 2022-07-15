# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-07-15 23:08:49
@LastEditors  : xupingmao
@LastEditTime : 2022-07-16 00:02:21
@FilePath     : /xnote/handlers/note/dao_category.py
@Description  : 描述
"""

from xutils import Storage
from xutils import fsutil
from xutils import dbutil

dbutil.register_table("note_category", "笔记类目")
dbutil.register_table_index("note_category", "user_name")

_db = dbutil.get_table("note_category")
_cat_config = fsutil.load_prop_config("config/note/category.properties")

def upsert_category(user_name, category):
    assert user_name != None
    assert category != None
    assert category.user_name != None

    if category._id == None:
        return _db.insert(category)
    return _db.update(category)

def list_category(user_name):
    assert user_name != None
    assert isinstance(user_name, str)
    
    cat_dict = dict()
    for key in _cat_config:
        value = _cat_config[key]
        cat_dict[key] = Storage(code=key, name=value, user_name=user_name)

    for item in _db.list_by_index("user_name", index_value=user_name, limit=-1):
        cat_dict[item.code] = item
    
    result = [Storage(code="all", name="全部")]
    for key in sorted(cat_dict.keys()):
        item = cat_dict.get(key)
        result.append(item)
    return result

def get_category_by_code(user_name, code):
    assert user_name != None
    assert code != None
    for item in list_category(user_name):
        if item.code == code:
            return item
    return None