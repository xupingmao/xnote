# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2021/12/27 23:34:03
@LastEditors  : xupingmao
@LastEditTime : 2022-12-10 16:57:57
@FilePath     : /xnote/core/xtables_new.py
@Description  : 描述
"""

import xutils
from xutils import dbutil


@xutils.log_init_deco("xtables_new")
def init():
    # 使用NoSQL风格的数据库接口
    # 数据库索引保证最终一致，不保证强一致
    dbutil.register_table("sys_log", "系统日志")
    dbutil.register_table("dict", "词典")

    # 文件相关
    db = dbutil.register_table("fs_index", "文件索引")
    db.register_index("ftype", "类型索引")
    # 网络文件映射到本地文件
    dbutil.register_table("fs_map", "文件映射")
    dbutil.register_table("fs_ctype", "缓存的Content-Type")
    dbutil.register_table("txt_info", "txt文件信息")

    # 用户信息
    dbutil.register_table("user", "用户信息表")
    dbutil.register_table("user_config", "用户配置表")
    dbutil.register_table("session", "用户会话信息")
    dbutil.register_table("user_session_rel", "用户会话关系")
    dbutil.register_table("user_stat", "用户数据统计")

    # 笔记信息
    dbutil.register_table("note_tags", "笔记标签绑定",
                          category="note", user_attr="user")
    dbutil.register_table("note_tag_meta", "笔记标签",
                          category="note", user_attr="user")
    dbutil.register_table("note_draft", "笔记草稿", category="note")
    dbutil.register_table("note_lock", "笔记编辑锁", category="note")

    # ID维度笔记索引
    db = dbutil.register_table(
        "note_index", "笔记索引，不包含内容 <note_index:note_id>", category="note")
    db.register_index("parent_id", "父级笔记ID")

    # 用户维度笔记索引
    db = dbutil.register_table("note_tiny", "用户维度的笔记索引 <table:user:id>",
                               category="note", check_user=True, user_attr="creator")
    db.register_index("name")
    db.register_index("ctime")
    db.register_index("parent_id")

    # 笔记修改历史
    dbutil.register_table("note_history_index", "笔记历史索引", category="note")
    dbutil.register_table("search_history", "搜索历史")

    # 分享关系
    db = dbutil.register_table("note_share", "笔记分享", category="note")
    db.register_index("note_id", "笔记ID")
    db.register_index("to_user", "分享的目标用户")

    # 统计数据
    db = dbutil.register_table("plugin_visit_log", "插件访问日志", user_attr="user", check_user = True)
    db.register_index("url", "页面URL")

    # 月度计划
    db = dbutil.register_table("month_plan", "月度计划", user_attr="user", check_user=True)

    # 重建索引(系统会根据索引版本增量构建)
    build_index_async()


@xutils.async_func_deco()
def build_index_async():
    dbutil.get_table("note_index").rebuild_index("v2")
    dbutil.get_table("note_tiny").rebuild_index("v2")
    dbutil.get_table("plugin_visit_log").rebuild_index("v1")
