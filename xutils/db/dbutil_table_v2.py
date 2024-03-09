# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-10-28 09:54:54
@LastEditors  : xupingmao
@LastEditTime : 2024-03-10 00:42:58
@FilePath     : /xnote/xutils/db/dbutil_table_v2.py
@Description  : 数据库表-API
"""

from xutils import Storage
from xutils.db.dbutil_base import *
from xutils.db.encode import (
    decode_str,
    encode_str,
    clean_value_before_update
)
from xutils.db.binlog import BinLog

class KvTableV2:
    """基于SQL+KV的表
    - 索引使用SQL维护
    - 数据使用KV维护
    """

    def __init__(self, table_name):
        # 参数检查
        table_info = get_table_info(table_name)
        assert table_info != None
        assert table_info.index_db != None

        self.table_name = table_name
        self.key_name = "_key"
        self.id_name = "_id"
        self.prefix = table_name + ":"
        self.table_info = table_info
        self.binlog = BinLog.get_instance()
        self.binlog_enabled = True
        self.index_column_names = table_info.index_db.get_column_names()
        self.index_db = table_info.index_db

    def set_binlog_enabled(self, enabled=True):
        self.binlog_enabled = enabled

    def _build_key(self, id):
        return self.prefix + str(id)

    def _get_key_from_obj(self, obj):
        validate_dict(obj, "obj is not dict")
        return obj.get(self.key_name)

    def _get_id_from_obj(self, obj):
        key = self._get_key_from_obj(obj)
        return key.rsplit(":", 1)[-1]
    
    def _get_int_id_from_obj(self, obj):
        id = self._get_id_from_obj(obj)
        return int(id)

    def _get_id_from_key(self, key):
        return decode_str(key.rsplit(":", 1)[-1])

    def _get_int_id_from_key(self, key):
        id_str = self._get_id_from_key(key)
        return int(id_str)

    def _format_value(self, key, value):
        if not isinstance(value, dict):
            value = Storage(_raw=value)

        value[self.key_name] = key
        value[self.id_name] = self._get_id_from_key(key)
        return value

    def _convert_to_db_row(self, obj):
        obj_copy = dict(**obj)
        clean_value_before_update(obj_copy)
        return obj_copy

    def _check_before_delete(self, key):
        if not key.startswith(self.prefix):
            raise Exception("invalid key:%s" % key)

    def _check_value(self, obj, key=""):
        if not isinstance(obj, dict):
            raise Exception("key:%r, invalid obj:%r, expected dict" % (key, obj))

    def _check_key(self, key):
        if not key.startswith(self.prefix):
            raise Exception("invalid key:(%s), prefix:(%s)" %
                            (key, self.prefix))

    def _put_obj(self, key, obj, sync=False, fix_index=False):
        # ~~写redo-log，启动的时候要先锁定检查redo-log，恢复异常关闭的数据~~
        # 不需要重新实现redo-log，直接用leveldb的批量处理功能即可
        # 使用leveldb的批量操作可以确保不会读到未提交的数据
        batch = create_write_batch()
        old_obj = db_get(key)
        self._format_value(key, old_obj)
        batch.put(key, self._convert_to_db_row(obj))
        if self.binlog_enabled:
            self.binlog.add_log(
                "put", key, obj, batch=batch, old_value=old_obj)
        # 更新批量操作
        batch.commit(sync)
        
        if fix_index:
            self.rebuild_record_index(key, obj)
        else:
            self.update_index(obj)

    def is_valid_key(self, key=None):
        assert isinstance(key, str)
        return key.startswith(self.prefix)

    def get_by_id(self, row_id, default_value=None):
        """通过ID查询记录
        :param row_id: 记录ID
        :param default_value: 默认值
        """
        row_id = str(row_id)
        key = self._build_key(row_id)
        result = self.get_by_key(key, default_value)
        if result == None:
            index_result = self.index_db.select_first(where=dict(id=row_id))
            if index_result != None:
                return self._format_value(key, index_result)
        return result

    def batch_get_by_id(self, row_id_list, default_value=None):
        key_list = []
        key_id_dict = {}
        for row_id in row_id_list:
            q_row_id = str(row_id)
            key = self._build_key(q_row_id)
            key_list.append(key)
            key_id_dict[key] = row_id

        result = dict()
        key_result = self.batch_get_by_key(
            key_list, default_value=default_value)
        for key in key_result:
            object = key_result.get(key)
            id = key_id_dict.get(key)
            result[id] = object
        return result
    
    def batch_get_by_index_list(self, row_list, default_value=None):
        key_list = []
        dict_result = {}

        for row in row_list:
            q_row_id = str(row.id)
            key = self._build_key(q_row_id)
            key_list.append(key)
            dict_result[key] = self._format_value(key, row)

        kv_dict_result = self.batch_get_by_key(
            key_list, default_value=default_value)
        dict_result.update(kv_dict_result)
        
        result = []
        for key in key_list:
            object = dict_result.get(key)
            if object != None:
                result.append(object)
        return result

    def get_by_key(self, key, default_value=None):
        """通过key查询记录
        :param key: kv数据库的key
        :param default_value: 默认值
        """
        if key == "":
            return None
        self._check_key(key)
        value = db_get(key, default_value)
        if value is None:
            return None

        return self._format_value(key, value)

    def batch_get_by_key(self, key_list, default_value=None):
        for key in key_list:
            self._check_key(key)

        batch_result = db_batch_get(key_list, default_value)
        for key in batch_result:
            value = batch_result.get(key)
            if value is None:
                batch_result[key] = None
                continue
            batch_result[key] = self._format_value(key, value)

        return batch_result
    
    def build_sql_record(self, obj):
        result = {}
        for attr in self.index_column_names:
            result[attr] = obj.get(attr) # None值也需要写入
        return result

    def insert(self, obj):
        """插入新数据
        @param {object} obj 插入的对象
        @param {string} id_type id类型
        """
        self._check_value(obj)
        sql_record = self.build_sql_record(obj)
        # 必须先插入索引，有两个目的:
        # 1. 获取主键ID
        # 2. 如果插入索引成功，插入主数据失败，可以在列表上做删除操作
        new_id = self.index_db.insert(**sql_record)
        new_id_str = str(new_id)
        key = self._build_key(new_id_str)
        obj[self.key_name] = key
        obj[self.id_name] = new_id_str

        self._put_obj(key, obj)
        return new_id

    def put(self, obj, fix_index=False):
        """从`obj`中获取主键`key`进行更新"""
        self._check_value(obj)

        obj_key = self._get_key_from_obj(obj)
        assert isinstance(obj_key, str), "obj_key must be str"
        
        self._check_key(obj_key)
        self._put_obj(obj_key, obj, fix_index=fix_index)

    update = put

    def put_by_id(self, id, obj, encode_key=True):
        """通过ID进行更新，如果key包含用户，必须有user_name(初始化定义或者传入参数)
        :param {str} id: 指定ID
        :param {dict} obj: 写入的对象
        :param encode_key=True: 是否对key进行编码,用于处理特殊字符
        """
        id = str(id)
        if encode_key:
            id = encode_str(id)

        key = self._build_key(id)
        self.put_by_key(key, obj)

    def put_by_key(self, key, obj, fix_index=False):
        """直接通过`key`进行更新"""
        self._check_key(key)
        self._check_value(obj, key=key)

        obj[self.key_name] = key
        obj[self.id_name] = self._get_id_from_key(key)
        
        update_obj = obj
        self._put_obj(key, update_obj, fix_index=fix_index)

    def delete(self, obj):
        obj_key = self._get_key_from_obj(obj)
        self.delete_by_key(obj_key)

    def batch_delete(self, obj_list=[]):
        if len(obj_list) == 0:
            return
        keys = []
        ids = []
        for obj in obj_list:
            key = self._get_key_from_obj(obj)
            id = self._get_int_id_from_obj(obj)
            keys.append(key)
            ids.append(id)
        db_batch_delete(keys)
        self.index_db.delete(where="id in $ids", vars=dict(ids=ids))

    def delete_by_id(self, id):
        id = str(id)
        key = self._build_key(id)
        self.delete_by_key(key)

    def delete_by_key(self, key):
        """通过key删除记录: 这里先删除记录，然后删除索引，如果删除记录成功，删除索引失败，还可以在列表发起重试"""
        validate_str(key, "delete_by_key: invalid key")
        self._check_before_delete(key)

        old_obj = self.get_by_key(key)
        if old_obj is None:
            self.delete_index_by_key(key)
            return

        id = self._get_int_id_from_obj(old_obj)
        self._format_value(key, old_obj)
        batch = create_write_batch()
        # 更新批量操作
        batch.delete(key)
        if self.binlog_enabled:
            self.binlog.add_log("delete", key, old_obj,
                                batch=batch, old_value=old_obj)
        batch.commit()
        self.index_db.delete(where=dict(id=id))

    def delete_index_by_key(self, key):
        id = self._get_int_id_from_key(key)
        self.index_db.delete(where=dict(id=id))

    def update_index(self, record):
        sql_record = self.build_sql_record(record)
        id = self._get_int_id_from_obj(record)
        self.index_db.update(where=dict(id=id), **sql_record)

    def select(self, where=None, vars=None, offset=0, limit=10, order=None):
        rows = self.index_db.select(where=where, vars=vars, order=order, offset=offset, limit=limit)
        return self.batch_get_by_index_list(rows)

    def select_first(self, where=None, vars=None, order="id"):
        index_record = self.index_db.select_first(where=where, vars=vars, order=order, offset=0, limit=1)
        if index_record == None:
            return None
        kv_record = self.get_by_id(index_record.id)
        if kv_record == None:
            key = self._build_key(index_record.id)
            return self._format_value(key, index_record)
        return kv_record

    def iter_by_index(self, where="", vars=None, batch_size=20):
        """内部接口"""
        assert isinstance(where, str)
        last_id = 0
        while True:
            this_vars = dict(last_id = last_id)
            if vars != None:
                this_vars.update(vars)
            index_records = self.index_db.select(where = "id > $last_id " + where, vars = this_vars, limit = batch_size, order="id")
            if len(index_records) == 0:
                break
            result_list = self.batch_get_by_index_list(index_records)
            for item in result_list:
                yield item
            last_id = result_list[-1].id
    
    def iter_by_kv(self, limit=-1):
        """内部接口"""
        for key, item in prefix_iter(self.prefix, include_key=True, limit=limit):
            yield self._format_value(key, item)

    def rebuild_index(self, version="v1", **kw):
        """重建索引
        :param version="v1": 版本
        :param ignore_error=False: 忽略错误
        :param ignore_invalid_id=False: 忽略无效的ID
        """
        idx_version_key = "_idx_version:%s" % self.table_name
        current_version = db_get(idx_version_key)
        if current_version == version:
            logging.info("当前索引已经是最新版本, table=%s, version=%s" %
                            (self.table_name, version))
            return
        self.rebuild_index_no_check(**kw)
        db_put(idx_version_key, version)
        logging.info("索引重建完成, table=%s", self.table_name)

    def rebuild_index_no_check(self, **kw):
        # TODO 可以通过复制表的方式重建索引,减少数据库的锁时间
        for key, item in prefix_iter(self.prefix, include_key=True):
            self.rebuild_record_index(key, item, **kw)

    def rebuild_record_index(self, key, item, **kw):
        ignore_invalid_id = kw.get("ignore_invalid_id", False)
        ignore_error = kw.get("ignore_error", False)
        
        """重建单条记录的索引"""
        sql_record = self.build_sql_record(item)
        try:
            id = self._get_int_id_from_key(key)
        except ValueError as e:
            if ignore_invalid_id or ignore_error:
                logging.warning("invalid key=%s", key)
                return
            else:
                raise e
        old_index = self.index_db.select_first(where=dict(id=id))
        try:
            if old_index == None:
                sql_record["id"] = id
                self.index_db.insert(**sql_record)
            else:
                self.index_db.update(where=dict(id=id), **sql_record)
        except Exception as e:
            if ignore_error:
                logging.warning("err=%s",e)
                return
            else:
                raise e
