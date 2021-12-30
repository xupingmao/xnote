# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/27 23:34:03
# @modified 2021/12/28 23:54:11
# @filename xtables_new.py

import xutils
from xutils import dbutil

dbutil.register_table("dict", "词典")

def get_global_dict_table():
    db = dbutil.get_table("dict")
    # id_value 是字典的 key
    # content_zh 中文含义
    # content_en 英文含义
    return db


@xutils.log_init_deco("xtables")
def init():
    pass