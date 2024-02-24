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


class ErrorLog(Storage):

    def __init__(self, **kw):
        super().__init__(**kw)
        self.key = ""
        self.value = ""
        self.ctime = "1970-01-01 00:00:00"
        self.type = "exception"
        self.err_msg = "error"

class TableIndexRepair:
    """表索引修复工具，不是标准功能，所以抽象到一个新的类里面"""

    def __init__(self, db, error_db):
        self.db = db
        self.repair_error_db = error_db
        self.table_name = ""
        self.debug = False
    
    def current_time(self):
        return time.strftime('%Y-%m-%d %H:%M:%S')

    def repair_index(self):
        try:
            self.do_repair_index()
        except:
            err_msg = xutils.print_exc()
            error_log = ErrorLog()
            error_log.ctime = self.current_time()
            error_log.err_msg = err_msg
            self.repair_error_db.insert(error_log)

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
                        error_log = ErrorLog()
                        error_log.key = key
                        error_log.value = value
                        error_log.type = "record"
                        error_log.ctime = self.current_time()
                        self.repair_error_db.insert(error_log)
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
        if self.debug:
            logging.info("Delete {%s}", key)

        if not self.is_index_key(key):
            logging.warning("Invalid index key:(%s)", key)
            return
        db_delete(key)
    
    def is_index_key(self, key):
        return key.startswith("_index$") or key.startswith(self.table_name + "$")

    def get_record_attr(self, record, key):
        # TODO 要改成按照 columns 去组装索引的值
        if isinstance(record, dict):
            return record.get(key)
        if hasattr(record, key):
            return getattr(record, key)
        return None

    def delete_invalid_index(self, index_name, index_prefix):
        db = self.db
        index_info = dbutil_base.IndexInfo.get_table_index_info(self.table_name, index_name)
        assert isinstance(index_info, IndexInfo)
        index = TableIndex(index_info)

        for old_key, index_object in prefix_iter(index_prefix, include_key=True):
            if isinstance(index_object, dict):
                # copy
                record = index_object.get("value")
                record_key = index_object.get("key")
            else:
                # ref
                record_key = index_object
                record = db_get(record_key)
            
            # record_key是主数据的key
                
            if record is None:
                logging.debug("empty record, key:(%s), record_id:(%s)",
                              old_key, record_key)
                self.do_delete(old_key)
                continue

            if not isinstance(record_key, str):
                logging.debug("invalid record key, key:(%s), record_id:(%s)",
                              old_key, record_key)
                self.do_delete(old_key)
                continue

            user_name = None
            encoded_index_value = index.get_index_value(record)
            record_id = db._get_id_from_key(record_key)

            if db._need_check_user:
                try:
                    parser = KeyParser(record_key)
                    table_name = parser.pop_left()
                    user_name = parser.pop_left()
                    user_name = decode_str(user_name)
                except:
                    logging.error("invalid key: (%s)", record_key)
                    error_log = ErrorLog()
                    error_log.key = old_key
                    error_log.value = str(record_key)
                    error_log.type = "index"
                    error_log.ctime = self.current_time()
                    self.repair_error_db.insert(error_log)
                    self.do_delete(old_key)
                    continue

            prefix = db._get_index_prefix(index_name, user_name)
            new_key = db._build_key_no_prefix(
                prefix, encoded_index_value, record_id)

            if new_key != old_key:
                logging.debug("index dismatch, key:(%s), record_id:(%s), correct_key:(%s)",
                              old_key, record_key, new_key)
                self.do_delete(old_key)

