# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2021/12/27 23:34:03
@LastEditors  : xupingmao
@LastEditTime : 2024-03-07 23:44:05
@FilePath     : /xnote/xnote/core/xtables_kv.py
@Description  : 数据库-KV表定义

TODO 支持使用sql维护索引 index_type = sql
"""

import xutils
from xutils import dbutil
from . import xtables

@xutils.log_init_deco("xtables_kv")
def init():
    # 使用NoSQL风格的数据库接口
    # NoSQL适合的场景：大文档、配置、缓存、计数器、时序日志
    # 尽量不要使用索引的功能，数据库索引保证最终一致，不保证强一致
    # 变更索引后需要调用 rebuild_index 方法
    init_system_table()
    init_note_tables()
    init_message_tables()
    # 初始化一些废弃的表，防止覆盖老版本数据
    init_deleted_table()
    
    # 网络文件映射到本地文件
    dbutil.register_table("fs_map", "文件映射")
    dbutil.register_table("fs_ctype", "缓存的Content-Type")
    
    txt_info_index = xtables.get_table_by_name("txt_info_index")
    dbutil.register_table("txt_info", "txt文件信息", index_db=txt_info_index)
    
    dbutil.register_table("fs_sync_index", "文件同步索引信息")
    
    dbutil.register_table("user_config", "用户配置表")
    db = dbutil.register_table("session", "用户会话信息")
    db.register_index("user", columns=["user_name"])
    dbutil.register_table("sys_config", "系统配置表")
    
    dbutil.register_table("user_stat", "用户数据统计")

    # 月度计划
    month_plan_index = xtables.get_table_by_name("month_plan_index")
    db = dbutil.register_table("month_plan", "月度计划", index_db=month_plan_index)
    dbutil.get_table_v2("month_plan").rebuild_index("v2", ignore_error=True)

def init_system_table():
    dbutil.register_table("sys_log", "系统日志")
    dbutil.register_table("dict", "词典")
    dbutil.register_table("migrate_failed", "迁移失败记录")
    db = dbutil.register_table("z", "老版本的zset实现")
    db.delete_table()

def init_deleted_table():
    # 统计数据
    db = dbutil.register_table("plugin_visit_log", "插件访问日志", user_attr="user", check_user = True)
    db.drop_index("url", comment = "页面URL")
    db.rebuild_index("v2")
    db.delete_table()

    db = dbutil.register_table("user_session_rel", "用户会话关系")
    db.delete_table()

    db = dbutil.register_table("note_skey", "用户维度的skey索引 <note_skey:user:skey>")
    db.delete_table()

    db = dbutil.register_table("msg_task_idx", "待办索引")
    db.delete_table()

    # 用户信息，迁移到了sql-db
    db = dbutil.register_table("user", "用户信息表")
    db.delete_table()

    # uv统计
    db = dbutil.register_table("uv", "uv访问统计")
    db.drop_index("date_ip", columns = ["date", "ip"])
    db.rebuild_index("v1")
    db.delete_table()

    # 文件相关，废弃，新的使用sql-db
    db = dbutil.register_table("fs_index", "文件索引")
    db.drop_index("ftype", comment = "类型索引")
    db.delete_table()
    
    # 插件访问日志,新的SQL表参考 page_visit_log
    db = dbutil.register_table("plugin_visit", "插件访问日志")
    db.drop_index("k_url", columns=["user", "url"])
    db.rebuild_index("v2")
    db.delete_table()
    
    # 操作日志
    db = dbutil.register_table("user_op_log", "用户操作日志表", user_attr="user_name")
    db.delete_table()
    
def init_note_tables():
    # 笔记信息
    dbutil.register_table("note_tags", "笔记标签绑定",
                          category="note", user_attr="user")
    dbutil.register_table("note_tag_meta", "笔记标签",
                          category="note", user_attr="user")
    dbutil.register_table("note_draft", "笔记草稿", category="note", type="hash")
    dbutil.register_table("note_lock", "笔记编辑锁", category="note")
    dbutil.register_table("note_full", "笔记的完整信息", category="note")

    # ID维度笔记索引
    db = dbutil.register_table(
        "note_index", "笔记索引，不包含内容", category="note")
    db.drop_index("parent_id", comment = "父级笔记ID")
    db.drop_index("name", columns=["creator", "name"])
    db.drop_index("ctime", columns=["creator", "ctime"])
    db.drop_index("skey", columns=["creator", "skey"])
    db.rebuild_index("v5")
    db.delete_table()

    # 用户维度笔记索引
    db = dbutil.register_table("note_tiny", "用户维度的笔记索引",
                               category="note", check_user=True, user_attr="creator")
    db.drop_index("name")
    db.drop_index("ctime")
    db.drop_index("parent_id")
    db.rebuild_index("v3")
    db.delete_table()

    # 笔记修改历史
    dbutil.register_table("note_history_index", "笔记历史索引", category="note")
    dbutil.register_table("note_history", "笔记的历史版本", category="note")
    
    db = dbutil.register_table("search_history", "搜索历史", user_attr="user", check_user=True)
    db.drop_index("user", comment = "使用二级key的表,不需要user索引")

    # 分享关系
    db = dbutil.register_table("note_share", "笔记分享", category="note")
    db.drop_index("note_id", comment = "笔记ID")
    db.drop_index("to_user", comment = "分享的目标用户")
    db.rebuild_index("v1")
    db.delete_table()


    db = dbutil.register_table("comment", "评论模型", category="note")
    db.drop_index("user", comment = "用户索引")
    db.drop_index("note_id", comment = "笔记ID索引")

    # 公共笔记
    db = dbutil.register_table("note_public", "公共笔记", category="note")
    db.drop_index("hot_index")
    db.drop_index("share_time")
    db.rebuild_index("v1")
    db.delete_table()

    # 操作日志
    db = dbutil.register_table("user_note_log", "用户笔记操作日志", check_user=True, user_attr="user")
    db.drop_index("visit_cnt")
    db.drop_index("atime")
    db.drop_index("mtime")
    db.drop_index("ctime")
    db.rebuild_index("v1")
    db.delete_table()

    # 笔记类目（已删除）
    db = dbutil.register_table("note_category", "笔记类目", category="note", 
                               check_user=True, user_attr="user_name")
    db.delete_table()

def init_message_tables():
    dbutil.register_table("message", "短文本", check_user=True, user_attr="user")
    dbutil.register_table("msg_key", "备忘关键字/标签", check_user=True, user_attr="user")
    
    db = dbutil.register_table("msg_backup", "随手记备份", check_user=True, user_attr="user")
    db.delete_table()

    dbutil.register_table("msg_search_history", "备忘搜索历史", check_user=True, user_attr="user")
    
    msg_history_index = xtables.get_table_by_name("msg_history_index")
    dbutil.register_table("msg_history", "备忘历史", index_db=msg_history_index)

