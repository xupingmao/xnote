# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-10-03 22:51:40
@LastEditors  : xupingmao
@LastEditTime : 2022-10-03 22:59:06
@FilePath     : /xnote/xutils/db/dbutil_id_gen.py
@Description  : id生成
"""
import xutils
from xutils.db.dbutil_base import get_write_lock, db_get, db_put, validate_none, timeseq
from xutils.db.encode import encode_id

class IdGenerator:

    def __init__(self, table_name) -> None:
        self.table_name = table_name

    def create_increment_id(self, start_id=None):
        if start_id != None:
            assert start_id > 0

        max_id_key = "_max_id:" + self.table_name

        with get_write_lock():
            last_id = db_get(max_id_key) # type: int
            if last_id is None:
                if start_id != None:
                    last_id = start_id
                else:
                    last_id = 1
            else:
                last_id += 1
            db_put(max_id_key, last_id)
            return encode_id(last_id)

    def create_new_id(self, id_type="uuid", id_value=None):
        if id_type == "uuid":
            validate_none(id_value, "invalid id_value")
            return xutils.create_uuid()

        if id_type == "timeseq":
            validate_none(id_value, "invalid id_value")
            return timeseq()

        if id_type == "auto_increment":
            validate_none(id_value, "invalid id_value")
            return self.create_increment_id()

        if id_value != None:
            validate_none(id_type, "invalid id_type")
            return id_value

        raise Exception("unknown id_type:%s" % id_type)
