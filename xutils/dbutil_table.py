# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/04 21:22:40
# @modified 2021/12/04 21:59:27
# @filename dbutil_table.py

from xutils.dbutil_base import *

class LdbTable:
    """基于leveldb的表，比较常见的是以下几种
    * key = prefix:record_id           全局数据库
    * key = prefix:user_name:record_id 用户维度数据
    * key = prefix:user_name:folder_id:record_id 用户+文件夹维度数据

    字段说明: 
    * prefix    代表的是功能类型，比如猫和狗是两种不同的动物，锤子和手机是两种不同的工具
    * user_name 代表用户名，比如张三和李四
    * folder_id 代表用户定义的目录，比如张三有两个不同的项目
    * record_id 代表一条记录的ID
    """

    def __init__(self, table_name, user_name = None, key_name = "_key"):
        # 参数检查
        check_table_name(table_name)

        self.table_name = table_name
        self.key_name = key_name

        self.prefix = table_name

        if user_name != None and user_name != "":
            self.prefix += ":" + user_name

        if self.prefix[-1] != ":":
            self.prefix += ":"

    def build_key(self, *argv):
        return self.prefix + ":".join(argv)

    def _get_key_from_obj(self, obj):
        if obj is None:
            raise Exception("obj can not be None")

        return getattr(obj, self.key_name)

    def _format_value(self, key, value):
        if not isinstance(value, dict):
            value = Storage(_raw = value)

        setattr(value, self.key_name, key)
        return value

    def _get_result_from_tuple_list(self, tuple_list):
        result = []
        for key, value in tuple_list:
            self._format_value(key, value)
            result.append(value)
        return result

    def _get_update_obj(self, obj):
        return obj

    def _get_id_value(self, id_type = "uuid"):
        if id_type == "uuid":
            return xutils.create_uuid()
        elif id_type == "timeseq":
            return timeseq()
        else:
            raise Exception("unknown id_type:%s" % id_type)

    def _check_before_delete(self, key):
        if not key.startswith(self.prefix):
            raise Exception("invalid key:%s" % key)

    def _check_value(self, obj):
        if not isinstance(obj, dict):
            raise Exception("invalid obj:%s, expected dict" % type(obj))

    def is_valid_key(self, key = None, user_name = None):
        if user_name is None:
            return key.startswith(self.prefix)
        else:
            return key.startswith(self.prefix + user_name)

    def get_by_key(self, key, default_value = None):
        value = get(key, default_value)
        if value is None:
            return None

        self._format_value(key, value)
        return value

    def insert(self, obj, id_type = "timeseq"):
        self._check_value(obj)
        id_value = self._get_id_value(id_type)
        key  = self.build_key(id_value)
        put(key, obj)
        return key

    def insert_by_user(self, user_name, obj, id_type = "timeseq"):
        assert user_name != None
        self._check_value(obj)
        id_value = self._get_id_value(id_type)
        key  = self.build_key(user_name, id_value)
        put(key, obj)
        return key

    def update(self, obj):
        """从`obj`中获取主键`key`进行更新"""
        self._check_value(obj)
        obj_key = self._get_key_from_obj(obj)
        update_obj = self._get_update_obj(obj)
        put(obj_key, update_obj)

    def update_by_key(self, key, obj):
        """直接通过`key`进行更新"""
        self._check_value(obj)
        update_obj = self._get_update_obj(obj)
        put(key, update_obj)

    def delete(self, obj):
        obj_key = self._get_key_from_obj(obj)
        self._check_before_delete(obj_key)
        delete(obj_key)

    def delete_by_key(self, key):
        self._check_before_delete(key)
        delete(key)

    def iter(self, offset = 0, limit = 20, reverse = False, key_from = None, filter_func = None):
        if key_from == "":
            key_from = None

        if key_from != None:
            key_from = self.build_key(key_from)

        for key, value in prefix_iter(self.prefix, None, offset, limit, 
                reverse = reverse, include_key = True, key_from = key_from):
            self._format_value(key, value)
            yield value

    def list(self, *args, **kw):
        result = []
        for value in self.iter(*args, **kw):
            result.append(value)
        return result

    def list_by_user(self, user_name, offset = 0, limit = 20, reverse = False):
        tuple_list = prefix_list(self.prefix + user_name, None, offset, limit, reverse = reverse, include_key = True)
        return self._get_result_from_tuple_list(tuple_list)

    def list_by_func(self, user_name, filter_func = None, offset = 0, limit = 20, reverse = False):
        tuple_list = prefix_list(self.prefix + user_name, filter_func, offset, limit, reverse = reverse, include_key = True)
        return self._get_result_from_tuple_list(tuple_list)

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

