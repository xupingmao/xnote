# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2021/12/27 23:34:03
@LastEditors  : xupingmao
@LastEditTime : 2022-08-28 16:37:21
@FilePath     : /xnote/core/xtables_new.py
@Description  : 描述
"""

import xutils
from xutils import dbutil


@xutils.log_init_deco("xtables_new")
def init():
    # 数据库索引保证最终一致，不保证强一致
    dbutil.register_table("dict", "词典")
    dbutil.register_table("user_stat", "用户数据统计")
    dbutil.register_table("note_tags", "笔记标签绑定", category="note", user_attr="user")
    dbutil.register_table("note_tag_meta", "笔记标签", category="note", user_attr="user")

    db = dbutil.register_table("fs_index", "文件索引")
    db.register_index("ftype", "类型索引")
