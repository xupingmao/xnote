# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/04 15:36:42
# @modified 2021/12/11 11:10:20
# @filename dbutil.py
from xutils.db.dbutil_base import *
from xutils.db.dbutil_table import *
from xutils.db.dbutil_hash import *
from xutils.db.dbutil_sortedset import *


def _get_table_no_lock(table_name):
    table = LDB_TABLE_DICT.get(table_name)
    if table is None:
        table = LdbTable(table_name)
    return table


def get_table_old(table_name, type="rdb"):
    """获取table对象
    @param {str} table_name 表名
    @return {LdbTable}
    """
    check_table_name(table_name)

    if type == "hash":
        return get_hash_table(table_name)

    table = LDB_TABLE_DICT.get(table_name)
    if table is None:
        with get_write_lock():
            table = _get_table_no_lock(table_name)
            LDB_TABLE_DICT[table_name] = table
    return table


def get_table(table_name, type="rdb", user_name=None):
    """获取table对象
    @param {str} table_name 表名
    @return {LdbTable|LdbHashTable}
    """
    check_table_name(table_name)

    if type == "hash":
        return get_hash_table(table_name)

    return LdbTable(table_name, user_name=user_name)


def get_hash_table(table_name, user_name=None):
    return LdbHashTable(table_name, user_name=user_name)
