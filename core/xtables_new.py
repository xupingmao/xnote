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

    # 文件相关
    db = dbutil.register_table("fs_index", "文件索引")
    db.register_index("ftype", "类型索引")
    # 网络文件映射到本地文件
    dbutil.register_table("fs_map", "文件映射")
    dbutil.register_table("fs_ctype", "缓存的Content-Type")

    # 用户信息
    dbutil.register_table("user", "用户信息表")
    dbutil.register_table("user_config", "用户配置表")
    dbutil.register_table("session", "用户会话信息")
    dbutil.register_table("user_session_rel", "用户会话关系")
    dbutil.register_table("user_stat", "用户数据统计")

    # 笔记信息
    dbutil.register_table("note_tags", "笔记标签绑定", category="note", user_attr="user")
    dbutil.register_table("note_tag_meta", "笔记标签", category="note", user_attr="user")
    dbutil.register_table("note_draft", "笔记草稿", category = "note")
    dbutil.register_table("note_lock", "笔记编辑锁", category = "note")
    # 分享关系
    db = dbutil.register_table("note_share", "笔记分享", category = "note")
    db.register_index("note_id", "笔记ID")
    db.register_index("to_user", "分享的目标用户")
