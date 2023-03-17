# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-22 22:04:41
@LastEditors  : xupingmao
@LastEditTime : 2022-11-26 19:13:10
@FilePath     : /xnote/xutils/db/dbutil_table_index.py
@Description  : 表索引管理
                - [x] 引用索引
                - [x] 聚集索引支持
                - [] 联合索引支持
                - [] 列表索引支持
"""

import logging
import xutils
from xutils.db.encode import encode_index_value, clean_value_before_update, decode_str
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

from .driver_interface import BatchInterface

class TableIndex:

    def __init__(self, index_info: IndexInfo, user_attr=None, check_user=False,index_type="ref"):
        table_name = index_info.table_name
        index_name = index_info.index_name

        self.index_info = index_info
        self.user_attr = user_attr
        self.index_name = index_name
        self.table_name = table_name
        self.key_name = "_key"
        self.check_user = check_user
        self.prefix = IndexInfo.build_prefix(self.table_name, index_name)
        self.index_type = index_type
        self.index_info = index_info

        if check_user and user_attr == None:
            raise Exception("user_attr没有注册, table_name:%s" % table_name)

    def _get_prefix(self, user_name=None):
        prefix = self.prefix

        if user_name != None:
            prefix += ":" + encode_index_value(user_name)

        return prefix

    def _get_key_from_obj(self, obj):
        validate_dict(obj, "obj is not dict")
        return obj.get(self.key_name)

    def _get_id_from_obj(self, obj):
        key = self._get_key_from_obj(obj)
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
    
    def get_index_value(self, obj) -> str:
        if len(self.index_info.columns) > 1:
            result = []
            for colname in self.index_info.columns:
                value = obj.get(colname)
                result.append(encode_index_value(value))
            return ",".join(result)
        else:
            value = obj.get(self.index_name)
            return encode_index_value(value)

    def update_index(self, old_obj, new_obj, batch: BatchInterface, force_update=False):
        index_name = self.index_name
        assert isinstance(new_obj, dict)

        validate_obj(new_obj, "invalid new_obj")

        # 插入的时候old_obj为空
        obj_id = self._get_id_from_obj(new_obj)
        obj_key = self._get_key_from_obj(new_obj)
        validate_str(obj_id, "invalid obj_id")
        escaped_obj_id = encode_index_value(obj_id)
        user_name = self._get_user_name(new_obj)

        index_prefix = self._get_prefix(user_name=user_name)
        old_value = None
        new_value = None

        if old_obj != None and isinstance(old_obj, dict):
            # 旧的数据必须为dict类型
            old_value = self.get_index_value(old_obj)

        new_value = self.get_index_value(new_obj)

        # 索引值是否变化
        index_changed = (new_value != old_value)
        need_update = self.index_type == "copy" or index_changed

        if not need_update:
            logging.debug("index value unchanged, index_name:(%s), value:(%s)",
                          index_name, old_value)
            if not force_update:
                return

        assert isinstance(new_value, str)
        # 只要有旧的记录，就要清空旧索引值
        if old_value != None and index_changed:
            old_index_key = index_prefix + ":" + old_value + ":" + escaped_obj_id
            batch.check_and_delete(old_index_key)

        if self.index_info.ignore_none_value and new_value == chr(0):
            # None值不处理
            return

        # 新的索引值始终更新
        new_index_key = index_prefix + ":" + new_value + ":" + escaped_obj_id

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

        user_name = self._get_user_name(old_obj)

        obj_id = self._get_id_from_obj(old_obj)
        escaped_obj_id = encode_index_value(obj_id)

        old_value = old_obj.get(self.index_name)
        old_value = encode_index_value(old_value)
        index_prefix = self._get_prefix(user_name)
        index_key = index_prefix + ":" + old_value + ":" + escaped_obj_id
        batch.delete(index_key)
    
    def drop(self):
        for key, value in prefix_iter(self.prefix, limit=-1, include_key=True):
            db_delete(key)



class TableIndexRepair:
    """表索引修复工具，不是标准功能，所以抽象到一个新的类里面"""

    def __init__(self, db, error_db):
        self.db = db
        self.repair_error_db = error_db

    def repair_index(self):
        try:
            self.do_repair_index()
        except:
            err_msg = xutils.print_exc()
            error_log = dict(err_msg=err_msg, type="exception")
            self.repair_error_db.insert(
                error_log, id_type="auto_increment")

    def do_repair_index(self):
        db = self.db

        if len(db.index_names) == 0:
            return

        # 先删除无效的索引，这样速度更快
        for name in db.index_names:
            prefix1 = "_index$%s$%s" % (db.table_name, name)      # v1版本的索引前缀
            prefix2 = IndexInfo.build_prefix(db.table_name, name) # v2版本的索引前缀
            self.delete_invalid_index(name, prefix1)
            self.delete_invalid_index(name, prefix2)

        for value in db.iter(limit=-1):
            if db._need_check_user:
                key = value._key
                assert xutils.is_str(key)
                try:
                    parts = key.split(":")
                    if len(parts) != 3:
                        logging.error("invalid key: %s", key)
                        error_log = dict(key=key, value=value, type="record")
                        self.repair_error_db.insert(
                            error_log, id_type="auto_increment")
                        db_delete(key)
                        continue
                    table_name, user_name, id = key.split(":")
                    user_name = decode_str(user_name)
                except ValueError:
                    xutils.print_exc()
                    logging.error("invalid record key: %s", key)
                    continue
                db.rebuild_single_index(value, user_name=user_name)
            else:
                db.rebuild_single_index(value)
        
        # 清理count缓存
        for name in db.index_names:
            delete_index_count_cache(db.table_name, name)

    def do_delete(self, key):
        logging.info("Delete {%s}", key)

        if not key.startswith("_index$"):
            logging.warning("Invalid index key:(%s)", key)
            return
        db_delete(key)
    
    def get_record_attr(self, record, key):
        if isinstance(record, dict):
            return record.get(key)
        return getattr(record, key)

    def delete_invalid_index(self, index_name, index_prefix):
        db = self.db

        for old_key, index_object in prefix_iter(index_prefix, include_key=True):
            if isinstance(index_object, dict):
                # copy
                record = index_object.get("value")
                record_key = index_object.get("key")
            else:
                # ref
                record_key = index_object
                record = db_get(record_key)
                
            if record is None:
                logging.debug("empty record, key:(%s), record_id:(%s)",
                              old_key, record_key)
                self.do_delete(old_key)
                continue

            user_name = None
            index_value = self.get_record_attr(record, index_name)
            record_id = db._get_id_from_key(record_key)

            if db._need_check_user:
                try:
                    table_name, user_name, id = record_key.split(":")
                    user_name = decode_str(user_name)
                except:
                    logging.error("invalid key: (%s)", record_key)
                    error_log = dict(
                        key=old_key, value=record_key, type="index")
                    self.repair_error_db.insert(error_log)
                    self.do_delete(old_key)
                    continue

            prefix = db._get_index_prefix(index_name, user_name)
            new_key = db._build_key_no_prefix(
                prefix, encode_index_value(index_value), record_id)

            if new_key != old_key:
                logging.debug("index dismatch, key:(%s), record_id:(%s), correct_key:(%s)",
                              old_key, record_key, new_key)
                self.do_delete(old_key)

