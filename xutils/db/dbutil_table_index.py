# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-22 22:04:41
@LastEditors  : xupingmao
@LastEditTime : 2022-05-28 12:25:04
@FilePath     : /xnote/xutils/db/dbutil_table_index.py
@Description  : 表索引管理
"""

import logging
from xutils.db.encode import encode_index_value
from xutils.db.dbutil_base import validate_obj, validate_str, validate_dict


class TableIndex:

    def __init__(self, table_name=None, index_name=None, user_attr=None, check_user=False):
        assert table_name != None
        assert index_name != None

        self.user_attr = user_attr
        self.index_name = index_name
        self.table_name = table_name
        self.key_name = "_key"
        self.check_user = check_user
        self.prefix = "_index$%s$%s" % (self.table_name, index_name)

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
                raise Exception("({table_name}).{user_attr} is required".format(
                    table_name=self.table_name, user_attr=self.user_attr))
            return user_name
        else:
            return None

    def update_index(self, old_obj, new_obj, batch=None, force_update=False):
        index_name = self.index_name

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

        if old_obj != None:
            old_value = old_obj.get(index_name)

        if new_obj != None:
            new_value = new_obj.get(index_name)

        # 索引值是否变化
        index_changed = (new_value != old_value)

        if not index_changed:
            logging.debug("index value unchanged, index_name:(%s), value:(%s)",
                          index_name, old_value)
            if not force_update:
                return

        # 只要有旧的记录，就要清空旧索引值
        if old_obj != None and index_changed:
            old_value = encode_index_value(old_value)
            old_index_key = index_prefix + ":" + old_value + ":" + escaped_obj_id
            batch.check_and_delete(old_index_key)

        # 新的索引值始终更新
        new_value = encode_index_value(new_value)
        new_index_key = index_prefix + ":" + new_value + ":" + escaped_obj_id
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
