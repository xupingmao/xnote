# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-22 22:04:41
@LastEditors  : xupingmao
@LastEditTime : 2023-07-23 11:53:51
@FilePath     : /xnote/xutils/db/dbutil_table_index.py
@Description  : 表索引管理,不建议继续使用,推荐使用关系型数据库或者搜索引擎构建索引
                - [x] 引用索引
                - [x] 聚集索引支持
                - [x] 联合索引支持
"""

import logging
import xutils
import time
from xutils import Storage
from xutils.db.encode import encode_index_value, clean_value_before_update, decode_str, KeyParser
from xutils.db.dbutil_base import (
    db_delete, 
    db_get, 
    validate_obj, 
    validate_str, 
    validate_dict, 
    prefix_iter, 
    delete_index_count_cache,
    IndexInfo,
)
from xutils.db import dbutil_base
from xutils.interfaces import BatchInterface

class TableIndex:

    def __init__(self, index_info: IndexInfo):
        table_name = index_info.table_name
        index_name = index_info.index_name

        table_info = dbutil_base.TableInfo.get_by_name(table_name)
        assert table_info != None

        self.index_info = index_info
        self.user_attr = table_info.user_attr
        self.index_name = index_name
        self.table_name = table_name
        self.key_name = "_key"
        self.check_user = table_info.check_user
        self.prefix = IndexInfo.build_prefix(self.table_name, index_name)
        self.index_type = index_info.index_type
        self.index_info = index_info
        self.debug = False

        if self.check_user and self.user_attr == None:
            raise Exception("user_attr没有注册, table_name:%s" % table_name)

    def _get_prefix(self, user_name=None):
        prefix = self.prefix

        if user_name != None:
            prefix += ":" + encode_index_value(user_name)

        return prefix
    
    def get_prefix_by_obj(self, obj):
        prefix = self.prefix
        user_name = self._get_user_name(obj)
        if user_name != None:
            prefix += ":" + encode_index_value(user_name)

        return prefix
    

    def _get_key_from_obj(self, obj):
        validate_dict(obj, "obj is not dict")
        return obj.get(self.key_name)

    def _get_id_from_obj(self, obj):
        key = self._get_key_from_obj(obj)
        if key == None:
            return None
        return key.rsplit(":", 1)[-1]

    def _get_user_name(self, obj):
        if self.user_attr != None:
            user_name = obj.get(self.user_attr)
            if user_name == None:
                raise Exception("({table_name}).{user_attr} is required, obj:{obj}".format(
                    table_name=self.table_name, user_attr=self.user_attr, obj=obj))
            return user_name
        else:
            return None
    
    def get_index_key(self, obj: dict):
        assert obj != None
        assert isinstance(obj, dict)

        encoded_value = self.get_index_value(obj)
        obj_id = self._get_id_from_obj(obj)
        encoded_id = encode_index_value(obj_id)
        index_prefix = self.get_prefix_by_obj(obj)
        index_key = index_prefix + ":" + encoded_value + ":" + encoded_id
        return index_key, encoded_value
    
    def get_index_value(self, obj) -> str:
        if len(self.index_info.columns) > 1:
            result = []
            for colname in self.index_info.columns:
                value = obj.get(colname)
                result.append(encode_index_value(value))
            return ",".join(result)
        else:
            index_attr = self.index_info.columns[0]
            value = obj.get(index_attr)
            return encode_index_value(value)

    def update_index(self, old_obj, new_obj: dict, batch: BatchInterface, force_update=False):
        index_name = self.index_name
        assert isinstance(new_obj, dict), "new_obj must be dict"

        # 插入的时候old_obj为空
        obj_id = self._get_id_from_obj(new_obj)
        obj_key = self._get_key_from_obj(new_obj)
        validate_str(obj_id, "invalid obj_id")

        old_index_key = ""
        new_index_key, new_index_value = self.get_index_key(new_obj)

        if old_obj != None and isinstance(old_obj, dict):
            # 旧的数据必须为dict类型
            old_index_key, _ = self.get_index_key(old_obj)

        # 索引值是否变化
        index_changed = (new_index_key != old_index_key)
        need_update = self.index_type == "copy" or index_changed

        if not need_update:
            if self.debug:
                logging.debug("index value unchanged, index_name:(%s), value:(%s)",
                            index_name, old_index_key)
            if not force_update:
                return

        assert isinstance(new_index_key, str)

        # 只要有旧的记录，就要清空旧索引值
        if old_index_key != "" and index_changed:
            batch.check_and_delete(old_index_key)

        if self.index_info.ignore_none_value and new_index_value == chr(0):
            # None值不处理
            return

        # 新的索引值始终更新
        if self.index_type == "copy":
            clean_obj = dict(**new_obj)
            clean_value_before_update(clean_obj)
            index_value = dict(key = obj_key, value = clean_obj)
            batch.check_and_put(new_index_key, index_value)
        else:
            # ref
            batch.check_and_put(new_index_key, obj_key)

    def delete_index(self, old_obj, batch):
        assert old_obj != None
        assert batch != None, "batch can not be None"
        if isinstance(old_obj, dict):
            index_key, _ = self.get_index_key(old_obj)
            batch.delete(index_key)
    
    def drop(self):
        for key, value in prefix_iter(self.prefix, limit=-1, include_key=True):
            db_delete(key)
