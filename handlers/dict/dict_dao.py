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
from xnote.core.models import SearchResult
from .models import DictDO, DictTypeEnum, DictTypeItem

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
    v = SearchResult()
    v.name = f"定义: {item.key}"
    v.value = item.value
    v.summary = item.value
    v.mtime = item.mtime
    v.ctime = item.ctime
    v.url = f"/dict/update?dict_id={item.id}"
    v.raw = item.value
    v.icon = "icon-dict"
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

class DictDaoClass:

    def __init__(self, dict_type: DictTypeItem):
        self.dict_type = dict_type
        self.db = xtables.get_table_by_name(self.dict_type.table_name)

    def to_fuzzy(self, key: str):
        if not key.startswith("%"):
            key = "%" + key
        if not key.endswith("%"):
            key = key + "%"
        return key

    def create(self, dict_item: DictDO):
        now = dateutil.format_datetime()
        dict_item.ctime = now
        dict_item.mtime = now

        save_dict = dict_item.get_save_dict()
        if not self.dict_type.has_user_id:
            save_dict.pop("user_id", None)
        else:
            assert save_dict["user_id"] > 0
        dict_id = int(self.db.insert(**save_dict))
        dict_item.dict_id = dict_id
        return dict_id
    
    def update(self, dict_id=0, user_id=0, value=""):
        now = dateutil.format_datetime()
        where_dict = {
            self.db.table_info.pk_name: dict_id,
        }
        if self.dict_type.has_user_id:
            where_dict["user_id"] = user_id
            
        return self.db.update(where=where_dict, value=value, mtime=now)

    def get_by_id(self, dict_id=0, user_id=0):
        assert dict_id > 0
        where_dict = {
            self.db.table_info.pk_name: dict_id,
        }
        result = self.db.select_first(where=where_dict)
        if result is None:
            return None
        return DictDO.from_dict(result, dict_type=self.dict_type.value)
    
    def delete_by_id(self, dict_id=0):
        assert dict_id > 0
        where_dict = {
            self.db.table_info.pk_name: dict_id,
        }
        return self.db.delete(where=where_dict)

    def find_one(self, user_id=0, key=""):
        results, _ = self.find_page(user_id=user_id, key=key, limit=1, skip_count=True)
        if len(results) > 0:
            return results[0]
        return None
    
    def find_page(self, user_id=0, key="", fuzzy_key="", offset=0, limit=20, skip_count=False):
        assert user_id > 0
        where = "1=1"
        if self.dict_type.has_user_id:
            where += " AND user_id=$user_id"
        if key != "":
            where += " AND `key`=$key"
        if fuzzy_key != "":
            where += " AND `key` LIKE $fuzzy_key"
            fuzzy_key = self.to_fuzzy(fuzzy_key)
        
        vars = dict(user_id=user_id, key=key, fuzzy_key=fuzzy_key)
        db_result = self.db.select(where=where, vars=vars, offset=offset, limit=limit)
        if skip_count:
            amount = 0
        else:
            amount = self.db.count(where=where, vars=vars)
        return DictDO.from_dict_list(db_result, dict_type=self.dict_type.value), amount

DictPublicDao = DictDaoClass(DictTypeEnum.public)
DictPersonalDao = DictDaoClass(DictTypeEnum.personal)
DictRelevantDao = DictDaoClass(DictTypeEnum.relevant)

def get_dao_by_type(dict_type=""):
    if dict_type == DictTypeEnum.personal.value:
        return DictPersonalDao
    if dict_type == DictTypeEnum.relevant.value:
        return DictRelevantDao
    
    return DictPublicDao