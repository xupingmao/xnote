# -*- coding:utf-8 -*-
# Created by xupingmao on 2017/03/15
# @modified 2021/11/07 14:14:15
"""Xnote的数据库配置(此模块已经废弃)
    考虑到持续运行的维护，增加表结构需要非常慎重
    考虑清楚你需要的是数据还是配置，如果是配置建议通过扩展脚本配置xconfig
"""
import os
import xutils
import xconfig
import web.db
import sqlite3
from xutils.sqldb import SqliteTableManager as TableManager
from xutils.sqldb import TableProxy

def init_test_table():
    """测试数据库"""
    path = os.path.join(xconfig.DATA_DIR, "test.db")
    with TableManager("test", dbpath = path) as manager:
        manager.add_column("id1", "integer", 0)
        manager.add_column("int_value", "int", 0)
        manager.add_column("float_value", "float")
        manager.add_column("text_value", "text", "")
        manager.add_column("name", "text", "test")
        manager.add_column("check", "text", "aaa'bbb")
        manager.add_index("check")


def init_file_table():
    with TableManager("file", dbpath = xconfig.DB_PATH) as manager:
        manager.add_column("name",    "text", "")
        # 纯文本，用于搜索, 已废弃，移动到note_content
        manager.add_column("content", "text", "")
        # 原始的数据，比如带标签的HTML，还有图片等的base64数据，已废弃，移动到note_content
        manager.add_column("data", "text", "")
        # 文本内容长度或者子页面数量
        manager.add_column("size",    "long", 0)
        # 修改版本
        manager.add_column("version",  "int", 0)
        # 类型, markdown, post, mailist, file
        # 类型为file时，content值为文件的web路径
        manager.add_column("type", "text", "")

        # 关联关系
        # 上级目录
        manager.add_column("parent_id", "int", 0)
        # 使用file_tag表,兼容老代码,这里作为一个关键词存储，支持搜索
        manager.add_column("related", "text", "")
        # 创建时间ctime
        manager.add_column("ctime", "text", "")
        # 修改时间mtime
        manager.add_column("mtime", "text", "")
        # 访问时间atime
        manager.add_column("atime", "text", "")
        # 访问次数
        manager.add_column("visited_cnt", "int", 0)
        # 逻辑删除标记
        manager.add_column("is_deleted", "int", 0)
        # 是否公开
        manager.add_column("is_public", "int", 0)
        # 权限相关
        # 创建者
        manager.add_column("creator", "text", "")
        # 修改者
        # manager.add_column("modifier", "text", "")
        # 可以访问的角色, 如果是公开的则为public, 删除的为deleted
        manager.add_column("role", "text", "")
        # 置顶顺序
        manager.add_column("priority", "int", 0)

        # 各种索引
        manager.add_index(["parent_id", "name"])
        manager.add_index(["creator", "mtime", "type", "is_deleted"])
        manager.add_index(["creator", "type"])
        manager.add_index(["role", "mtime"])
        manager.add_index("ctime")
        # 虽然不能加速匹配过程，但是可以加速全表扫描
        manager.add_index("name")


def init_note_content_table():
    with TableManager("note_content", dbpath = xconfig.DB_PATH) as manager:
        # 纯文本，用于搜索
        manager.add_column("content", "text", "")
        # 原始的数据，比如带标签的HTML，还有图片等的base64数据
        manager.add_column("data", "text", "")


def init_note_history_table():
    dbpath = os.path.join(xconfig.DATA_DIR, "record.db")
    with TableManager("note_history", dbpath = dbpath) as manager:
        manager.add_column("note_id", "int", 0)
        manager.add_column("name",    "text", "")
        manager.add_column("content", "text", "")
        manager.add_column("mtime",   "text", "")
        manager.add_column("version", "int", 0)
        manager.add_index(["note_id", "version"])


def init_marked_file_table():
    # @since 2018/03/02
    with TableManager("marked_file", dbpath = xconfig.DB_PATH) as manager:
        manager.add_column("user", "text", "")
        manager.add_column("file_id", "int", 0)
        manager.add_column("name",  "text", "")
        manager.add_column("ctime", "text", "")


def init_tag_table():
    # 标签表，可以用于一些特征的标记
    # 2017/04/18
    with TableManager("file_tag", no_pk=True, dbpath = xconfig.DB_PATH) as manager:
        # 标签名
        manager.add_column("name",      "text", "")
        # 标签ID
        manager.add_column("file_id",   "int", 0)
        manager.add_column("user",      "text", "")
        manager.add_column("is_public", "int", 0)
        # 权限控制，标签不做用户区分, groups字段暂时废弃
        # manager.add_column("groups",  "text", "")


def init_schedule_table():
    # 2017/05/24
    # task是计划任务
    # Job是已经触发的任务,倾向于一次性的
    with TableManager("schedule", dbpath = xconfig.DB_PATH) as manager:
        manager.add_column("name", "text", "")
        manager.add_column("url", "text", "")
        manager.add_column("ctime", "text", "")
        manager.add_column("mtime", "text", "")
        manager.add_column("tm_wday", "text", "")  # Week Day no-repeat 一次性任务
        manager.add_column("tm_hour", "text", "")
        manager.add_column("tm_min",  "text", "")
        # 任务是否生效，用于一次性活动
        manager.add_column("active", "int", 1)
        manager.add_column("creator", "text", "")
        # 2017.10.21
        manager.add_column("message", "text", "")  # 提醒消息
        manager.add_column("sound", "int", 0)  # 是否语音提醒
        manager.add_column("webpage", "int", 0)  # 是否网页提醒


def init_history_table():
    # 2017/05/21
    dbpath = os.path.join(xconfig.DATA_DIR, "record.db")
    with TableManager("history", dbpath = dbpath) as manager:
        manager.add_column("type", "text", "")
        manager.add_column("key",  "text", "")
        manager.add_column("user", "text", "")
        manager.add_column("ctime", "text", "")
        # 耗时
        manager.add_column("rt", "int", 0)


def init_user_table():
    # 2017/05/21
    # 简单的用户表
    with TableManager("user", dbpath = xconfig.DB_PATH) as manager:
        manager.add_column("name",       "text", "")
        manager.add_column("password",   "text", "")
        manager.add_column("salt",       "text", "")
        # 额外的访问权限
        manager.add_column("privileges", "text", "")
        manager.add_column("ctime",      "text", "")
        manager.add_column("mtime",      "text", "")
        manager.add_column("token",      "text", "")
        manager.add_column("login_time", "text", "")


def init_message_table():
    """
    用来存储比较短的消息,消息和资料库的主要区别是消息存储较短的单一信息
    - 消息支持状态
    - 2017/05/29
    """
    with TableManager("message", dbpath = xconfig.DB_PATH) as manager:
        manager.add_column("ctime", "text", "")
        manager.add_column("mtime", "text", "")
        manager.add_column("user",  "text", "")
        # 用一个状态可以拍成一排
        # 消息的状态 0关注 50挂起 100已完成
        manager.add_column("status", "int", 0)
        manager.add_column("content", "text", "")
        # IP地址
        manager.add_column("ip", "text", "")
        # 地址信息
        manager.add_column("location", "text", "")
        # 索引
        manager.add_index(["user", "ctime", "status"])
        manager.add_index(["user", "status"])


def init_collection_table():
    # 2017/12/09
    # 通用的收藏数据结构，基于file的收藏只能收藏file而且不能支持多用户
    with TableManager("collection", dbpath = xconfig.DB_PATH) as manager:
        manager.add_column("user", "text", "")
        manager.add_column("name", "text", "")
        manager.add_column("link", "text", "")
        manager.add_column("type", "text", "")


def init_record_table():
    # 日志库和主库隔离开
    dbpath = os.path.join(xconfig.DATA_DIR, "record.db")
    with TableManager("record", dbpath = dbpath) as manager:
        manager.add_column("ctime", "text", "")
        # 添加单独的日期，方便统计用，尽量减少SQL函数的使用
        manager.add_column("cdate", "text", "")
        manager.add_column("type",  "text", "")
        # 自己把所有条件都组装到key里
        manager.add_column("key",  "text", "")
        manager.add_column("value", "text", "")
        # 索引
        manager.add_index(["type", "ctime"])


def init_storage_table():
    """通用的配置对象, 比词典多一个type，用来存储个人的一些设置之类的"""
    dbpath = xconfig.DB_PATH
    with TableManager("storage", dbpath = dbpath) as manager:
        manager.add_column("ctime", "text", "")
        manager.add_column("mtime", "text", "")
        manager.add_column("user",  "text", "")
        manager.add_column("type",  "text", "")
        manager.add_column("key",   "text", "")
        manager.add_column("value", "text", "")
        manager.add_index("key")


def init_dict_table():
    """词典，和主库隔离
    @since 2018/01/14
    """
    dbpath = xconfig.DICT_FILE
    with TableManager("dictionary", dbpath = dbpath) as manager:
        manager.add_column("ctime", "text", "")
        manager.add_column("mtime", "text", "")
        manager.add_column("key", "text", "")
        manager.add_column("value", "text", "")
        manager.add_index("key")


def init_search_rule_table():
    """搜索规则（智能文件夹）
    @since 2019/02/18
    """
    with TableManager("search_rule", dbpath = xconfig.DB_PATH) as manager:
        manager.add_column("ctime", "text", "")
        manager.add_column("mtime", "text", "")
        manager.add_column("user",  "text", "")
        manager.add_column("name", "text", "")
        manager.add_column("expression", "text", "")
        manager.add_index("user")

class DBPool:

    sqlite_pool = {}

    @classmethod
    def get_sqlite_db(cls, fname=""):
        assert fname != ""
        if fname in cls.sqlite_pool:
            return cls.sqlite_pool.get(fname)
        fpath = os.path.join(xconfig.FileConfig.sqlite_dir, fname)
        db = web.db.SqliteDB(db = fpath)
        cls.sqlite_pool[fname] = db
        return db

class MockedDB():
    """
    模拟的空数据库接口
    """

    def select(self, *args, **kw):
        from web.utils import IterBetter
        return IterBetter(iter([]))

    def select_first(self, *args, **kw):
        return None

    def update(self, *args, **kw):
        return 0

    def insert(self, *args, **kw):
        return None

    def query(self, *args, **kw):
        from web.utils import IterBetter
        return IterBetter(iter([]))

    def count(self, *args, **kw):
        return 0

    def delete(self, *args, **kw):
        return


def DBWrapper(dbpath, tablename):
    db = web.db.SqliteDB(db = dbpath)
    return TableProxy(db, tablename)

def get_file_table():
    return DBWrapper(xconfig.DB_PATH, "file")


def get_note_table():
    return get_file_table()


def get_note_history_table():
    dbpath = os.path.join(xconfig.DATA_DIR, "record.db")
    return DBWrapper(dbpath, "note_history")


def get_note_content_table():
    return DBWrapper(xconfig.DB_PATH, "note_content")


def get_file_tag_table():
    return DBWrapper(xconfig.DB_PATH, "file_tag")


def get_schedule_table():
    return DBWrapper(xconfig.DB_PATH, "schedule")


def get_user_table():
    return DBWrapper(xconfig.DB_PATH, "user")


def get_message_table():
    return DBWrapper(xconfig.DB_PATH, "message")


def get_record_table():
    dbpath = os.path.join(xconfig.DATA_DIR, "record.db")
    return DBWrapper(dbpath, "record")


def get_storage_table():
    return DBWrapper(xconfig.DB_PATH, "storage")


def get_dict_table():
    db = DBPool.get_sqlite_db("dictionary.db")
    return TableProxy(db, "dictionary")

def get_search_rule_table():
    return DBWrapper(xconfig.DB_PATH, "search_rule")


get_dictionary_table = get_dict_table


def get_table(name, dbpath=None):
    """获取数据库表，表的创建和访问不必在xtables中定义
    @since 2019/04/11
    """
    if dbpath is None:
        dbpath = xconfig.DB_FILE
    return DBWrapper(dbpath, name)

@xutils.log_init_deco("xtables")
def init():
    if sqlite3 is None:
        xconfig.errors.append("sqlite3依赖丢失,部分功能不可用")
        return

    web.db.config.debug_sql = False
    init_dict_table()
