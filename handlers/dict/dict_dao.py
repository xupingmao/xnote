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
from xutils import textutil

PAGE_SIZE = xconfig.PAGE_SIZE

def convert_dict_func(item: DictDO):
    v = item.to_search_result()
    v.name = f"公共词典: {item.key}"
    return v


def search_dict(key, offset = 0, limit = None):
    if limit is None:
        limit = PAGE_SIZE
    items, count = DictPublicDao.find_page(key=key, offset=offset, limit=limit)
    items = list(map(convert_dict_func, items))
    return items, count

def get_relevant_words(word: str):
    result = DictRelevantDao.find_one(key = word)
    if result != None:
        if "," in result.value:
            return result.value.split(",")
        return result.value.split()
    return []


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
        dict_item.dict_type = self.dict_type.int_value
        dict_item.key = dict_item.key.lower()

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
            "dict_type": self.dict_type.int_value,
        }
        if self.dict_type.has_user_id:
            where_dict["user_id"] = user_id
            
        return self.db.update(where=where_dict, value=value, mtime=now)

    def get_by_id(self, dict_id=0, user_id=0):
        assert dict_id > 0
        where_dict = {
            self.db.table_info.pk_name: dict_id,
            "dict_type": self.dict_type.int_value,
        }
        if self.dict_type.has_user_id:
            where_dict["user_id"] = user_id
        
        result = self.db.select_first(where=where_dict)
        if result is None:
            return None
        return DictDO.from_dict(result)
    
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
        if self.dict_type.has_user_id:
            assert user_id > 0

        key = key.lower()
        fuzzy_key = fuzzy_key.lower()

        where = "dict_type=$dict_type"
        if self.dict_type.has_user_id:
            where += " AND user_id=$user_id"
        if key != "":
            where += " AND `key`=$key"
        if fuzzy_key != "":
            where += " AND `key` LIKE $fuzzy_key"
            fuzzy_key = self.to_fuzzy(fuzzy_key)
        
        vars = dict(user_id=user_id, key=key, fuzzy_key=fuzzy_key, dict_type=self.dict_type.int_value)
        db_result = self.db.select(where=where, vars=vars, offset=offset, limit=limit)
        if skip_count:
            amount = 0
        else:
            amount = self.db.count(where=where, vars=vars)
        return DictDO.from_dict_list(db_result), amount

DictPublicDao = DictDaoClass(DictTypeEnum.public)
DictPersonalDao = DictDaoClass(DictTypeEnum.personal)
DictRelevantDao = DictDaoClass(DictTypeEnum.relevant)

def get_dao_by_type(dict_type=0):
    if dict_type == DictTypeEnum.personal.int_value:
        return DictPersonalDao
    if dict_type == DictTypeEnum.relevant.int_value:
        return DictRelevantDao
    
    return DictPublicDao