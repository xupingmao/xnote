# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/04 21:22:40
# @modified 2021/12/26 23:21:32
# @filename dbutil_table.py

from xutils.dbutil_base import *
from urllib.request import quote

register_table("_redo_log", "重做日志")
register_table("_index", "通用索引")


def dict_del(dict, key):
    if key in dict:
        del dict[key]

class LdbTable:
    """基于leveldb的表，比较常见的是以下几种
    * key = prefix:record_id           全局数据库
    * key = prefix:user_name:record_id 用户维度数据

    字段说明: 
    * prefix    代表的是功能类型，比如猫和狗是两种不同的动物，锤子和手机是两种
                不同的工具
    * user_name 代表用户名，比如张三和李四
    * record_id 代表一条记录的ID

    注: record_id建议使用全局ID，尽量避免多级主键，如果使用多级主键，移动记录会
        比较麻烦，要重新构建主键
    """

    def __init__(self, table_name, user_name = None, 
            key_name = "_key", id_name = "_id"):
        # 参数检查
        check_table_name(table_name)

        self.table_name = table_name
        self.key_name = key_name
        self.id_name  = id_name
        self.prefix = table_name
        self.user_name = user_name
        self.index_names = set()

        if user_name != None and user_name != "":
            self.prefix += ":" + user_name

        if self.prefix[-1] != ":":
            self.prefix += ":"

    def define_index(self, index_key):
        validate_str(index_key, "index_key must be str")
        self.index_names.add(index_key)

    def build_key(self, *argv):
        return self.prefix + ":".join(argv)

    def build_key_no_prefix(self, *argv):
        return ":".join(filter(None, argv))

    def _get_key_from_obj(self, obj):
        if obj is None:
            raise Exception("obj can not be None")

        return getattr(obj, self.key_name)

    def _format_value(self, key, value):
        if not isinstance(value, dict):
            value = Storage(_raw = value)

        value[self.key_name] = key
        return value

    def _get_result_from_tuple_list(self, tuple_list):
        result = []
        for key, value in tuple_list:
            value = self._format_value(key, value)
            result.append(value)
        return result

    def _convert_to_db_row(self, obj):
        obj_copy = dict(**obj)
        dict_del(obj_copy, self.key_name)
        dict_del(obj_copy, self.id_name)
        return obj_copy

    def _get_id_value(self, id_type = "uuid", id_value = None):
        if id_type == "uuid":
            validate_none(id_value, "invalid id_value")
            return xutils.create_uuid()
        elif id_type == "timeseq":
            validate_none(id_value, "invalid id_value")
            return timeseq()
        elif id_value != None:
            validate_none(id_type, "invalid id_type")
            return id_value
        else:
            raise Exception("unknown id_type:%s" % id_type)

    def _check_before_delete(self, key):
        if not key.startswith(self.prefix):
            raise Exception("invalid key:%s" % key)

    def _check_value(self, obj):
        if not isinstance(obj, dict):
            raise Exception("invalid obj:%r, expected dict" % type(obj))

    def _check_key(self, key):
        if not key.startswith(self.prefix):
            raise Exception("invalid key:%s" % key)

    def _check_index_name(self, index_name):
        validate_str(index_name, "invalid index_name:%r" % index_name)
        if index_name not in self.index_names:
            raise Exception("invalid index_name:%r" % index_name)

    def _get_index_prefix(self, index_name):
        self._check_index_name(index_name)
        return self.build_key_no_prefix("_index", self.table_name, 
            self.user_name, index_name)

    def _format_index_value(self, value):
        if isinstance(value, str):
            return value
        if isinstance(value, int):
            # 负数需要放在前面
            if value < 0:
                return "A%020d" % value
            else:
                return "B%020d" % value
        if isinstance(value, float):
            if value < 0:
                return "A%020.10f" % value
            else:
                return "B%020.10f" % value
        raise Exception("unknown index_type:%r" % type(value))

    def _escape_key(self, key):
        return quote(key)

    def _update_index(self, old_obj, new_obj, batch):
        if len(self.index_names) == 0:
            return

        validate_obj(new_obj, "invalid new_obj")

        obj_key = self._get_key_from_obj(new_obj)
        validate_str(obj_key, "invalid object_key")
        escaped_obj_key = self._escape_key(obj_key)

        for index_name in self.index_names:
            index_prefix = self._get_index_prefix(index_name)
            old_value = None
            new_value = None
            
            if old_obj != None:
                old_value = old_obj.get(index_name)

            if new_obj != None:
                new_value = new_obj.get(index_name)

            if new_value == old_value:
                print_debug_info("index value unchanged, index_name={}, value={}", index_name, old_value)
                continue

            if old_value != None:
                old_value = self._format_index_value(old_value)
                batch.delete(index_prefix + ":" + old_value + ":" + escaped_obj_key)

            if new_value != None:
                new_value = self._format_index_value(new_value)
                batch.put(index_prefix + ":" + new_value + ":" + escaped_obj_key, obj_key)


    def _put_obj(self, key, obj):
        # ~~写redo-log，启动的时候要先锁定检查redo-log，恢复异常关闭的数据~~
        # 不需要重新实现redo-log，直接用leveldb的批量处理功能即可
        # 使用leveldb的批量操作可以确保不会读到未提交的数据
        batch = create_write_batch()
        with get_write_lock(key):
            old_obj = get(key)
            batch.put(key, self._convert_to_db_row(obj))
            self._update_index(old_obj, obj, batch)
            # 更新批量操作
            commit_write_batch(batch)

    def is_valid_key(self, key = None, user_name = None):
        if user_name is None:
            return key.startswith(self.prefix)
        else:
            return key.startswith(self.prefix + user_name)

    def get_by_id(self, row_id, default_value = None):
        key = self.build_key(row_id)
        return self.get_by_key(key, default_value)

    def get_by_key(self, key, default_value = None):
        self._check_key(key)
        value = get(key, default_value)
        if value is None:
            return None

        return self._format_value(key, value)

    def insert(self, obj, id_type = "timeseq", id_value = None):
        self._check_value(obj)
        id_value = self._get_id_value(id_type, id_value)
        key  = self.build_key(id_value)

        obj[self.key_name] = key
        obj[self.id_name]  = id_value

        self._put_obj(key, obj)
        return key

    def insert_by_user(self, user_name, obj, id_type = "timeseq"):
        """不建议使用，建议初始化时设置user_name"""
        validate_str(user_name, "invalid user_name")
        self._check_value(obj)

        id_value = self._get_id_value(id_type)
        key  = self.build_key(user_name, id_value)
        self._put_obj(key, obj)
        return key

    def update(self, obj):
        """从`obj`中获取主键`key`进行更新"""
        self._check_value(obj)

        obj_key = self._get_key_from_obj(obj)
        self._check_key(obj_key)

        update_obj = self._convert_to_db_row(obj)

        self._put_obj(obj_key, update_obj)

    def update_by_id(self, id, obj):
        key = self.build_key(id)
        self.update_by_key(key, obj)

    def update_by_key(self, key, obj):
        """直接通过`key`进行更新"""
        self._check_key(key)
        self._check_value(obj)
        
        update_obj = self._convert_to_db_row(obj)
        self._put_obj(key, update_obj)

    def delete(self, obj):
        obj_key = self._get_key_from_obj(obj)
        self.delete_by_key(obj_key)

    def delete_by_id(self, id):
        validate_str(id, "delete_by_id: id is None")
        key = self.build_key(id)
        self.delete_by_key(key)

    def delete_by_key(self, key):
        validate_str(key, "delete_by_key: invalid key")
        self._check_before_delete(key)
        delete(key)

    def iter(self, offset = 0, limit = 20, reverse = False, key_from = None, filter_func = None):
        if key_from == "":
            key_from = None

        if key_from != None:
            key_from = self.build_key(key_from)

        for key, value in prefix_iter(self.prefix, filter_func, offset, limit, 
                reverse = reverse, include_key = True, key_from = key_from):
            yield self._format_value(key, value)

    def list(self, *args, **kw):
        result = []
        for value in self.iter(*args, **kw):
            result.append(value)
        return result

    def list_by_user(self, user_name, offset = 0, limit = 20, reverse = False):
        tuple_list = prefix_list(self.prefix + user_name, None, 
            offset, limit, reverse = reverse, include_key = True)
        return self._get_result_from_tuple_list(tuple_list)

    def list_by_func(self, user_name, filter_func = None, 
            offset = 0, limit = 20, reverse = False):
        tuple_list = prefix_list(self.prefix + user_name, filter_func, 
            offset, limit, reverse = reverse, include_key = True)
        return self._get_result_from_tuple_list(tuple_list)

    def list_by_index(self, index_name, filter_func = None, 
            offset = 0, limit = 20, reverse = False):
        """通过索引查询结果列表
        @param {str}  index_name 索引名称
        @param {func} filter_func 过滤函数
        @param {int}  offset 开始索引
        @param {int}  limit  返回记录限制
        @param {bool} reverse 是否逆向查询
        """
        prefix = self._get_index_prefix(index_name)
        key_list = prefix_list(prefix, filter_func, offset, limit, 
            reverse = reverse, include_key = False)
        result = []
        for key in key_list:
            obj = self.get_by_key(key)
            result.append(obj)
        return result

    def count(self):
        return count_table(self.prefix)

    def count_by_user(self, user_name):
        return count_table(self.prefix + user_name)

    def count_by_func(self, user_name, filter_func):
        assert filter_func != None, "[count_by_func.assert] filter_func != None"
        return prefix_count(self.prefix + user_name, filter_func)


class PrefixedDb(LdbTable):
    """plyvel中叫做prefixed_db"""
    pass




