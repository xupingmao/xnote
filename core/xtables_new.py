# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2021/12/27 23:34:03
@LastEditors  : xupingmao
@LastEditTime : 2022-07-18 22:29:57
@FilePath     : /xnote/core/xtables_new.py
@Description  : 描述
"""

import xutils
from xutils import dbutil


@xutils.log_init_deco("xtables_new")
def init():
    dbutil.register_table("dict", "词典")
    dbutil.register_table("user_stat", "用户数据统计")