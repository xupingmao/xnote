# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2021-12-04 21:22:40
@LastEditors  : xupingmao
@LastEditTime : 2023-12-24 15:53:03
@FilePath     : /xnote/xutils/db/dbutil_table.py
@Description  : 数据库表-API, 不建议使用, 建议使用 dbutil_table_v2
"""

from urllib.parse import quote
from xutils import Storage
from xutils.db.dbutil_base import *
from xutils.db.dbutil_table_index import TableIndex, TableIndexRepair
from xutils.db.encode import (
    decode_str,
    encode_index_value,
    encode_str,
    clean_value_before_update
)
from xutils.db.dbutil_id_gen import IdGenerator
from xutils.db.binlog import BinLog
from xutils.db import filters

db = register_table("_id", "系统ID表")
db.delete_table()

register_table("_max_id", "最大ID")
register_table("_index", "通用索引")
register_table("_meta", "表元信息")
register_table("_idx_version", "索引版本")

db = register_table("_repair_error", "修复错误记录")
db.register_index("ctime")

class LdbTable:
    """Deprecated: 建议使用 dbutil_table_v2
    基于leveldb的表, 比较常见的是以下2种
    * key = prefix:record_id           全局数据库
    * key = prefix:user_name:record_id 用户(或者其他分片)维度数据

    字段说明: 
    * prefix    代表的是功能类型，比如猫和狗是两种不同的动物，锤子和手机是两种
                不同的工具
    * user_name 代表用户名，比如张三和李四，也可以是其他类型的对象ID，比如笔记ID
    * record_id 代表一条记录的ID，从属于user_name

    注: record_id建议使用全局ID，尽量避免多级主键，如果使用多级主键，移动记录会
        比较麻烦，要重新构建主键
    """

    def __init__(self, table_name, user_name=None):
        # 参数检查
        check_table_name(table_name)
        table_info = get_table_info(table_name)
        assert table_info != None

        self.table_name = table_name
        self.key_name = "_key"
        self.id_name = "_id"
        self.prefix = table_name
        self.user_name = user_name
        self.table_info = table_info
        self.index_names = table_info.get_index_names()
        self._need_check_user = table_info.check_user
        self.user_attr = None
        self.id_gen = IdGenerator(self.table_name)
        self.fix_user_attr = True
        # 自定义索引构建器
        self.build_index_func = None

        if table_info.check_user:
            if table_info.user_attr == None:
                raise Exception("table({table_name}).user_attr can not be None".format(
                    table_name=table_name))
            self.user_attr = table_info.user_attr

        self.binlog = BinLog.get_instance()
        self.binlog_enabled = True
        # TODO 索引用一个单例管理起来
        self.indexes = self._build_indexes() # type: list[TableIndex]

        if user_name != None:
            assert user_name != ""
            self.prefix += ":" + user_name

        if self.prefix[-1] != ":":
            self.prefix += ":"

    def _build_indexes(self):
        indexes = []
        index_dict = IndexInfo.get_table_index_dict(self.table_name)
        if index_dict != None:
            for index_name in index_dict:
                index_info = index_dict[index_name]
                indexes.append(TableIndex(index_info))
        return indexes

    def set_binlog_enabled(self, enabled=True):
        self.binlog_enabled = enabled

    def _build_key(self, *argv):
        return self.prefix + self._build_key_no_prefix(*argv)

    def _build_key_with_user(self, id, user_name):
        return self._build_key_no_prefix(self.table_name, user_name or self.user_name, id)

    def _build_key_no_prefix(self, *argv):
        return ":".join(filter(None, argv))

    def _get_key_from_obj(self, obj):
        validate_dict(obj, "obj is not dict")
        return obj.get(self.key_name)

    def _get_id_from_obj(self, obj):
        key = self._get_key_from_obj(obj)
        return key.rsplit(":", 1)[-1]

    def _get_id_from_key(self, key):
        return decode_str(key.rsplit(":", 1)[-1])

    def _get_user_from_key(self, key):
        parts = key.split(":")
        assert len(parts) == 3, parts
        return parts[1]

    def _format_value(self, key, value):
        if not isinstance(value, dict):
            value = Storage(_raw=value)

        value[self.key_name] = key
        value[self.id_name] = self._get_id_from_key(key)
        if self.user_attr != None and self.fix_user_attr:
            user = value.get(self.user_attr)
            parts = key.split(":")
            if user == None and len(parts) == 3:
                value[self.user_attr] = parts[1]
        return value

    def _convert_to_db_row(self, obj):
        obj_copy = dict(**obj)
        clean_value_before_update(obj_copy)
        return obj_copy

    def _create_new_id(self, id_type="uuid", id_value=None):
        return self.id_gen.create_new_id(id_type, id_value)

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

    def _check_index_name(self, index_name):
        validate_str(index_name, "invalid index_name:%r" % index_name)
        if index_name not in self.index_names:
            raise Exception("invalid index_name:%r" % index_name)

    def _check_user_name(self, user_name):
        user_name = self.user_name or user_name
        if self._need_check_user:
            validate_str(user_name, "invalid user_name:{!r}", user_name)

    def _get_prefix(self, user_name=None):
        user_name = self.user_name or user_name
        if user_name is None:
            return self.table_name + ":"
        else:
            return self.table_name + ":" + encode_str(user_name) + ":"

    def _update_index(self, old_obj, new_obj, batch, force_update=False):
        if self.build_index_func != None:
            self.build_index_func(new_obj=new_obj, old_obj=old_obj, force_update=force_update)
            return
        
        for index in self.indexes:
            index.update_index(old_obj, new_obj, batch, force_update)

    def _delete_index(self, old_obj, batch):
        for index in self.indexes:
            index.delete_index(old_obj, batch)

    def _put_obj(self, key, obj, sync=False):
        # ~~写redo-log，启动的时候要先锁定检查redo-log，恢复异常关闭的数据~~
        # 不需要重新实现redo-log，直接用leveldb的批量处理功能即可
        # 使用leveldb的批量操作可以确保不会读到未提交的数据
        batch = create_write_batch()
        with get_write_lock(key):
            old_obj = db_get(key)
            self._format_value(key, old_obj)
            batch.put(key, self._convert_to_db_row(obj))
            self._update_index(old_obj, obj, batch)
            if self.binlog_enabled:
                self.binlog.add_log(
                    "put", key, obj, batch=batch, old_value=old_obj)
            # 更新批量操作
            batch.commit(sync)

    def _insert_obj(self, key, obj, sync=False):
        # ~~写redo-log，启动的时候要先锁定检查redo-log，恢复异常关闭的数据~~
        # 不需要重新实现redo-log，直接用leveldb的批量处理功能即可
        # 使用leveldb的批量操作可以确保不会读到未提交的数据
        batch = create_write_batch()
        with get_write_lock(key):
            old_obj = db_get(key)
            self._format_value(key, old_obj)
            batch.insert(key, self._convert_to_db_row(obj))
            self._update_index(old_obj, obj, batch)
            if self.binlog_enabled:
                self.binlog.add_log(
                    "put", key, obj, batch=batch, old_value=old_obj)
            # 更新批量操作
            batch.commit(sync)

    def is_valid_key(self, key=None, user_name=None):
        assert isinstance(key, str)
        if user_name is None:
            return key.startswith(self.prefix)
        else:
            return key.startswith(self.prefix + user_name)

    def get_by_id(self, row_id, default_value=None, user_name=None):
        """通过ID查询记录
        :param row_id: 记录ID
        :param default_value: 默认值
        :param user_name: 用户标识
        """
        row_id = str(row_id)
        
        if self._need_check_user:
            validate_str(user_name, "invalid user_name:{!r}", user_name)

        row_id = encode_str(row_id)
        key = self._build_key_with_user(row_id, user_name=user_name)
        return self.get_by_key(key, default_value)

    def batch_get_by_id(self, row_id_list, default_value=None, user_name=None):
        for row_id in row_id_list:
            validate_str(row_id, "invalid row_id:{!r}", row_id)
            if self._need_check_user:
                validate_str(user_name, "invalid user_name:{!r}", user_name)

        key_list = []
        key_id_dict = {}
        for row_id in row_id_list:
            q_row_id = encode_str(row_id)
            key = self._build_key_with_user(q_row_id, user_name=user_name)
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

    def insert(self, obj, id_type="auto_increment", id_value=None, max_retry=10):
        """插入新数据
        @param {object} obj 插入的对象
        @param {string} id_type id类型
        """
        self._check_value(obj)

        if id_value != None:
            max_retry = 1

        user_name = None
        if self._need_check_user:
            user_name = obj.get(self.user_attr)

        new_id = "1"
        with get_write_lock(self.table_name):
            # TODO 优化加锁逻辑
            for i in range(max_retry):
                new_id = self.id_gen.create_new_id(id_type, id_value)
                key = self._build_key_with_user(new_id, user_name=user_name)
                conflict = self.get_by_key(key)
                if conflict != None:
                    continue

                obj[self.key_name] = key
                obj[self.id_name] = new_id

                self._put_obj(key, obj)
                return new_id
        raise Exception("insert conflict, id=%s" % new_id)

    def insert_by_user(self, user_name, obj, id_type="auto_increment"):
        """@deprecated 定义user_attr之后使用insert即可满足
        指定用户名插入数据
        """
        if self.user_name != None:
            raise Exception("table实例已经设置了user_name, 不能使用该方法")

        validate_str(user_name, "invalid user_name")
        self._check_value(obj)
            
        with get_write_lock(self.table_name):
            for i in range(10):
                new_id = self._create_new_id(id_type)
                key = self._build_key_with_user(new_id, user_name)
                conflict = self.get_by_key(key)
                if conflict != None:
                    continue
                self._put_obj(key, obj)
                return key
        raise Exception("insert conflict")

    def update(self, obj):
        """从`obj`中获取主键`key`进行更新"""
        self._check_value(obj)

        obj_key = self._get_key_from_obj(obj)
        assert isinstance(obj_key, str), "obj_key must be str"
        
        self._check_key(obj_key)

        self._put_obj(obj_key, obj)

    def put_by_id(self, id, obj, user_name=None, encode_key=True):
        """通过ID进行更新，如果key包含用户，必须有user_name(初始化定义或者传入参数)
        :param {str} id: 指定ID
        :param {dict} obj: 写入的对象
        :param {str|None} user_name: 用户分片
        :param encode_key=True: 是否对key进行编码,用于处理特殊字符
        """
        id = str(id)
        if self.user_name != None and user_name != None:
            raise DBException("table实例已经设置了user_name，不能再通过参数设置")

        if encode_key:
            id = encode_str(id)

        if self.user_attr != None:
            user_name = obj.get(self.user_attr)
            if user_name == None:
                raise DBException("%s属性未设置" % self.user_attr)

        self._check_user_name(user_name)
        key = self._build_key_with_user(id, user_name)
        self.update_by_key(key, obj)

    update_by_id = put_by_id

    def update_by_key(self, key, obj):
        """直接通过`key`进行更新"""
        self._check_key(key)
        self._check_value(obj, key=key)

        obj[self.key_name] = key
        obj[self.id_name] = self._get_id_from_key(key)
        
        update_obj = obj
        self._put_obj(key, update_obj)

    def rebuild_single_index(self, obj, user_name=None):
        self._check_value(obj)
        self._check_user_name(user_name)

        key = self._get_key_from_obj(obj)
        batch = create_write_batch()
        with get_write_lock(key):
            old_obj = get(key)
            self._format_value(key, obj)
            self._update_index(old_obj, obj, batch,
                               force_update=True)
            # 更新批量操作
            batch.commit()

    def repair_index(self):
        repair = TableIndexRepair(self, LdbTable("_repair_error"))
        repair.table_name = self.table_name
        repair.repair_index()

    def rebuild_index(self, version="v1"):
        """重建索引, 可以通过设置新的version值重新建立索引"""
        idx_version_key = "_idx_version:%s" % self.table_name
        current_version = db_get(idx_version_key)
        if current_version == version:
            logging.info("当前索引已经是最新版本, table=%s, version=%s" %
                            (self.table_name, version))
            return
        self.repair_index()
        db_put(idx_version_key, version)

    def delete(self, obj):
        obj_key = self._get_key_from_obj(obj)
        self.delete_by_key(obj_key)

    def batch_delete(self, obj_list=[]):
        if len(obj_list) == 0:
            return
        keys = []
        for obj in obj_list:
            key = self._get_key_from_obj(obj)
            keys.append(key)
        db_batch_delete(keys)

    def delete_by_id(self, id, user_name=None):
        id = str(id)
        key = self._build_key_with_user(id, user_name)
        self.delete_by_key(key)

    def delete_by_key(self, key, user_name=None):
        validate_str(key, "delete_by_key: invalid key")
        self._check_before_delete(key)
        assert self.is_valid_key(key, user_name), "key校验失败"

        old_obj = get(key)
        if old_obj is None:
            return

        self._format_value(key, old_obj)
        with get_write_lock(key):
            batch = create_write_batch()
            self._delete_index(old_obj, batch)
            # 更新批量操作
            batch.delete(key)
            if self.binlog_enabled:
                self.binlog.add_log("delete", key, old_obj,
                                    batch=batch, old_value=old_obj)
            batch.commit()

    def iter(self, offset=0, limit=20, reverse=False, key_from=None,
             filter_func=None, where = None, fill_cache=False, user_name=None):
        """返回一个遍历的迭代器
        :param {int} offset: 返回结果下标开始
        :param {int} limit:  返回结果最大数量
        :param {bool} reverse: 返回结果是否逆序
        :param {dict} where: where查询条件
        :param {str} key_from: 开始的key，这里是相对的key，也就是不包含table_name
        :param {func} filter_func: 过滤函数
        :param {str} user_name: 用户标识
        """
        if key_from == "":
            key_from = None

        if key_from != None:
            key_from = self._build_key(key_from)
        
        if user_name == None and where != None and self.user_attr != None:
            user_name = where.get(self.user_attr)

        if user_name != None:
            prefix = self.table_name + ":" + user_name
        else:
            prefix = self.prefix

        if where != None:
            filter_func = filters.create_func_by_where(where, filter_func)

        for key, value in prefix_iter(prefix, filter_func, offset, limit,
                                      reverse=reverse, include_key=True, key_from=key_from,
                                      fill_cache=fill_cache):
            yield self._format_value(key, value)

    def list(self, *args, **kw):
        """查询记录列表,参数和`iter`保持一致"""
        result = []
        for value in self.iter(*args, **kw):
            result.append(value)
        return result

    def get_first(self, filter_func=None, *, where = None, user_name=None):
        """读取第一个满足条件的数据"""
        result = self.list(limit=1, filter_func=filter_func, where = where,
                           user_name=user_name)
        if len(result) > 0:
            return result[0]
        else:
            return None
    
    def get_last(self, filter_func=None, *, user_name=None):
        """读取最后一个满足条件的数据"""
        result = self.list(limit=1, reverse=True,
                           filter_func=filter_func, user_name=user_name)
        if len(result) > 0:
            return result[0]
        else:
            return None

    def list_by_user(self, user_name, offset=0, limit=20, reverse=False):
        if self.user_name != None:
            raise Exception("table实例的user_name已经设置，不能使用该方法")

        return self.list(offset=offset, limit=limit, reverse=reverse, user_name=user_name)

    def list_by_func(self, user_name, filter_func=None,
                     offset=0, limit=20, reverse=False):
        return self.list(offset=offset, limit=limit, reverse=reverse,
                         filter_func=filter_func, user_name=user_name)

    def create_index_map_func(self, filter_func, where = None, index_type="ref"):
        if where != None:
            filter_func = filters.create_func_by_where(where, filter_func)

        def map_func_for_copy(batch_list):
            result = []
            for key, value in batch_list:
                obj_key = value.get("key")
                obj_value = value.get("value")
                self._format_value(obj_key, obj_value)
                if isinstance(obj_value, dict):
                    obj_value = Storage(**obj_value)

                # 这里应该是使用obj参数来过滤
                if filter_func == None:
                    is_match = True
                else:
                    is_match = filter_func(obj_key, obj_value)
                
                if is_match:
                    result.append((key, obj_value))

            return result

        def map_func_for_ref(batch_list):
            # 先判断实例是否存在
            # 普通的引用索引
            result = []
            key_list = []
            obj_dict = {}
            for key, ref_key in batch_list:
                key_list.append(ref_key)

            obj_dict = self.batch_get_by_key(key_list)

            for key, ref_key in batch_list:
                obj = obj_dict.get(ref_key)

                if obj is None:
                    # 异步 delete(key)
                    logging.warning("invalid key:(%s)", key)
                    continue

                # 检查key是否匹配
                obj_id = key.rsplit(":", 1)[-1]
                key_obj_id_temp = self._get_id_from_obj(obj)
                key_obj_id = quote(key_obj_id_temp)
                if obj_id != key_obj_id:
                    logging.warning(
                        "invalid obj_id:(%s), obj_id:(%s)", obj_id, key_obj_id)
                    continue
                
                self._format_value(ref_key, obj)

                # 用于调试
                # setattr(obj, "_idx_key", key)
                # 这里应该是使用obj参数来过滤
                if filter_func == None:
                    is_match = True
                else:
                    is_match = filter_func(key, obj)
                
                if is_match:
                    result.append((key, obj))
            return result

        if index_type == "copy":
            return map_func_for_copy

        return map_func_for_ref
    
    
    def _get_index_prefix(self, index_name, user_name=None):
        self._check_index_name(index_name)
        self._check_user_name(user_name)

        index_prefix = IndexInfo.build_prefix(self.table_name, index_name)
        return self._build_key_no_prefix(index_prefix, self.user_name or user_name)

    def _get_index_prefix_by_value(self, index_name, index_value, where = None, user_name=None):
        index_info = IndexInfo.get_table_index_info(self.table_name, index_name)
        assert index_info != None

        if self.user_attr != None and user_name == None and where != None:
            user_name = where.get(self.user_attr)

        if isinstance(index_value, dict):
            assert len(index_value) == 1, "只能设置1个属性"
            if index_value.get("$prefix") != None:
                prefix_value = index_value.get("$prefix")
                prefix_value_encoded = encode_index_value(prefix_value)
                return self._get_index_prefix(index_name, user_name=user_name) + ":" + prefix_value_encoded
            # TODO: 参考 mongodb 的 {$gt: 20} 这种格式的
            raise NotImplementedError("暂未实现")
        elif index_value != None:
            index_value = encode_index_value(index_value)
            return self._get_index_prefix(
                index_name, user_name=user_name) + ":" + index_value + ":"
        elif where != None:
            cols = []
            is_prefix_match = False
            for col in index_info.columns:
                col_value = where.get(col)
                if col_value == None:
                    break
                if isinstance(col_value, dict):
                    prefix = col_value.get("$prefix")
                    if prefix != None:
                        cols.append(prefix)
                        is_prefix_match = True
                        break
                cols.append(where.get(col))

            prefix_value_encoded = encode_index_value(cols)
            if is_prefix_match == False and len(cols) > 0 and len(cols) < len(index_info.columns):
                prefix_value_encoded += ","
            return self._get_index_prefix(index_name, user_name=user_name) + ":" + prefix_value_encoded
        else:
            return self._get_index_prefix(index_name, user_name=user_name) + ":"


    def count_by_index(self, index_name, filter_func=None, index_value=None, user_name=None, where = None):
        validate_str(index_name, "index_name can not be empty")
        index_info = IndexInfo.get_table_index_info(
            self.table_name, index_name)
        if index_info == None:
            raise Exception("index not found: %s" % index_name)

        prefix = self._get_index_prefix_by_value(index_name, index_value, where = where, user_name=user_name)
        map_func = self.create_index_map_func(
            filter_func, index_type=index_info.index_type, where = where)
        return prefix_count_batch(prefix, map_func=map_func)
    
    def list_by_index(self, index_name, filter_func=None,
                      offset=0, limit=20, *, reverse=False,
                      index_value=None, user_name=None, where = None):
        """通过索引查询结果列表
        @param {str}  index_name 索引名称
        @param {func} filter_func 过滤函数
        @param {int}  offset 开始索引
        @param {int}  limit  返回记录限制
        @param {bool} reverse 是否逆向查询
        """
        validate_str(index_name, "index_name can not be empty")
        index_info = IndexInfo.get_table_index_info(
            self.table_name, index_name)
        if index_info == None:
            raise Exception("index not found: %s" % index_name)

        prefix = self._get_index_prefix_by_value(index_name, index_value, where = where, user_name=user_name)
        map_func = self.create_index_map_func(
            filter_func, index_type=index_info.index_type, where = where)
        return list(prefix_iter_batch(prefix, offset=offset, limit=limit,
                                      map_func=map_func,
                                      reverse=reverse, include_key=False))

    def first_by_index(self, *args, **kw):
        kw["limit"] = 1
        result = self.list_by_index(*args, **kw)
        if len(result) > 0:
            return result[0]
        return None

    def count(self, filter_func=None, user_name=None, id_prefix=None, where = None):
        if user_name == None and where != None and self.user_attr != None:
            user_name = where.get(self.user_attr)

        prefix = self._get_prefix(user_name=user_name)
        if id_prefix != None:
            prefix += encode_str(id_prefix)
            
        if filter_func == None:
            return prefix_count_fast(prefix)

        return prefix_count(prefix, filter_func)

    def count_by_user(self, user_name):
        return self.count(user_name=user_name)

    def count_by_func(self, user_name, filter_func):
        assert filter_func != None, "[count_by_func.assert] filter_func != None"
        return self.count(user_name=user_name, filter_func=filter_func)

    def drop_index(self, index_name):
        for index in self.indexes:
            if index.index_name == index_name:
                index.drop()


class PrefixedDb(LdbTable):
    """plyvel中叫做prefixed_db"""
    pass


def insert(table_name, obj_value, sync=False):
    """往指定表里面插入一条新记录"""
    db = LdbTable(table_name)
    return db.insert(obj_value)


def prefix_iter_batch(prefix,  # type: str
                      offset=0,  # type: int
                      limit=-1,  # type: int
                      reverse=False,
                      include_key=False,
                      map_func=None,
                      fill_cache=False,
                      batch_size=100):
    """通过前缀迭代查询
    @param {string} prefix 遍历前缀
    @param {function} filter_func(str,object) 过滤函数
    @param {function} map_func(str,object)    映射函数，如果返回不为空则认为匹配
    @param {int} offset 选择的开始下标，包含
    @param {int} limit  选择的数据行数
    @param {boolean} reverse 是否反向遍历
    @param {boolean} include_key 返回的数据是否包含key，默认只有value
    """
    db = check_get_leveldb()
    prefix_str = prefix
    prefix_bytes = prefix.encode("utf-8")

    key_from = prefix_bytes
    key_to = prefix_bytes + b'\xff'

    iterator = db.RangeIter(key_from,
                            key_to,
                            include_value=True,
                            reverse=reverse,
                            fill_cache=fill_cache)

    matched_offset = 0
    result_size = 0

    def do_iter():
        batch_list = []
        for key, value in iterator:
            if not key.startswith(prefix_bytes):
                break
            key = key.decode("utf-8")
            obj = convert_bytes_to_object(value)
            if map_func == None:
                yield key, obj
            else:
                batch_list.append((key, obj))
                if len(batch_list) >= batch_size:
                    for key, value in map_func(batch_list):
                        yield key, value
                    batch_list = []

        if len(batch_list) > 0:
            assert map_func != None
            for key, obj in map_func(batch_list):
                yield key, obj

    for key, obj in do_iter():
        if matched_offset >= offset:
            result_size += 1
            if include_key:
                yield key, obj
            else:
                yield obj
        matched_offset += 1

        if limit > 0 and result_size >= limit:
            break

def prefix_count_batch(*args, **kw):
    count = 0
    kw["include_key"] = False
    for obj in prefix_iter_batch(*args, **kw):
        count+=1
    return count