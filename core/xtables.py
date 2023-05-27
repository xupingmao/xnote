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
from xutils.sqldb import TableManagerFacade as TableManager
from xutils.sqldb import TableProxy


class MySqliteDB(web.db.SqliteDB):
    dbpath = ""


def create_table_manager(table_name=""):
    assert table_name != ""
    dbpath = xconfig.FileConfig.get_db_path(table_name)
    db = get_db_instance(dbpath)
    return TableManager(table_name, db=db)


def get_db_instance(dbpath=""):
    db_driver = xconfig.get_system_config("db_driver")
    if db_driver == "mysql":
        db_host = xconfig.get_system_config("mysql_host")
        db_name = xconfig.get_system_config("mysql_database")
        db_user = xconfig.get_system_config("mysql_user")
        db_pw = xconfig.get_system_config("mysql_password")
        db_port = xconfig.get_system_config("mysql_port")
        db = web.db.MySQLDB(host=db_host, database=db_name,
                            user=db_user, pw=db_pw, port=db_port)
        db.dbname = "mysql"
        return db
    assert dbpath != ""
    db = MySqliteDB(db=dbpath)
    db.dbpath = dbpath
    return db


def get_table_by_name(table_name=""):
    # type: (str) -> TableProxy
    table_info = TableManager.get_table_info(table_name)
    if table_info == None:
        raise Exception("table not found: %s" % table_name)
    db = get_db_instance(dbpath=table_info.dbpath)
    return TableProxy(db, table_name)


def get_all_tables():
    """获取所有的sql-数据库代理实例"""
    result = []
    table_dict = TableManager.get_table_info_dict()
    for table_name in table_dict:
        proxy = get_table_by_name(table_name)
        result.append(proxy)
    return result


################################################
#  表定义
################################################

def init_test_table():
    """测试数据库"""
    table_name = "test"
    with create_table_manager(table_name) as manager:
        manager.add_column("int_value", "int", default_value=0)
        manager.add_column("float_value", "float", default_value=0.0)
        manager.add_column("text_value", "text", default_value="")
        manager.add_column("name", "text", default_value="test")
        manager.add_column("check", "text", default_value="aaa'bbb")
        manager.add_index("check")


def init_note_index_table():
    with create_table_manager("note_index") as manager:
        manager.add_column("name",    "varchar(255)", "")
        # 文本内容长度或者子页面数量
        manager.add_column("size",    "bigint", 0)
        # 修改版本
        manager.add_column("version",  "int", 0)
        # 类型, markdown, post, mailist, file
        # 类型为file时，content值为文件的web路径
        manager.add_column("type", "varchar(32)", "")

        # 关联关系
        # 上级目录
        manager.add_column("parent_id", "int", 0)
        # 创建时间ctime
        manager.add_column("ctime", "datetime", "1970-01-01 00:00:00")
        # 修改时间mtime
        manager.add_column("mtime", "datetime", "1970-01-01 00:00:00")
        # 访问时间atime
        manager.add_column("atime", "datetime", "1970-01-01 00:00:00")
        # 访问次数
        manager.add_column("visited_cnt", "int", 0)
        # 逻辑删除标记
        manager.add_column("is_deleted", "int", 0)
        # 创建者
        manager.add_column("creator", "varchar(64)", "")
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

        # 废弃字段
        manager.drop_column("content", "text", "")
        manager.drop_column("data", "text", "")


def init_tag_table():
    # 标签表，可以用于一些特征的标记
    # 2017/04/18
    with TableManager("file_tag", no_pk=True, dbpath=xconfig.DB_PATH) as manager:
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
    with TableManager("schedule", dbpath=xconfig.DB_PATH) as manager:
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


def init_user_table():
    # 2017/05/21
    # 简单的用户表
    with create_table_manager("user") as manager:
        manager.add_column("name",       "varchar(64)", "")
        manager.add_column("password",   "varchar(64)", "")
        manager.add_column("salt",       "varchar(64)", "")
        manager.add_column("ctime",      "datetime", "1970-01-01 00:00:00")
        manager.add_column("mtime",      "datetime", "1970-01-01 00:00:00")
        manager.add_column("token",      "varchar(32)", "")
        manager.add_column("login_time", "datetime", "1970-01-01 00:00:00")
        manager.add_index("name", is_unique=True)
        manager.add_index("token")
        # 删除的字段
        manager.drop_column("privileges", "text", "")


def init_message_table():
    """
    用来存储比较短的消息,消息和资料库的主要区别是消息存储较短的单一信息
    - 消息支持状态
    - 2017/05/29
    """
    table_name = "message"
    with create_table_manager(table_name) as manager:
        manager.add_column("ctime", "datetime", "1970-01-01 00:00:00")
        manager.add_column("mtime", "datetime", "1970-01-01 00:00:00")
        manager.add_column("user",  "varchar(64)", "")
        # 用一个状态可以拍成一排
        # 消息的状态 0关注 50挂起 100已完成
        manager.add_column("status", "int", 0)
        manager.add_column("content", "text", "")
        # IP地址
        manager.add_column("ip", "varchar(32)", "")
        # 地址信息
        manager.add_column("location", "varchar(255)", "")
        # 索引
        manager.add_index(["user", "ctime", "status"])
        manager.add_index(["user", "status"])


def init_record_table():
    # 日志库和主库隔离开
    with create_table_manager("record") as manager:
        manager.add_column("ctime", "datetime", "1970-01-01 00:00:00")
        # 添加单独的日期，方便统计用，尽量减少SQL函数的使用
        manager.add_column("cdate", "date", "1970-01-01")
        manager.add_column("type",  "varchar(64)", "")
        # 自己把所有条件都组装到key里
        manager.add_column("key",  "varchar(100)", "")
        manager.add_column("value", "text", "")
        # 索引
        manager.add_index(["type", "ctime"])


def init_dict_table():
    """词典，和主库隔离
    @since 2018/01/14
    """
    with create_table_manager("dictionary") as manager:
        manager.add_column("ctime", "datetime", "1970-01-01 00:00:00")
        manager.add_column("mtime", "datetime", "1970-01-01 00:00:00")
        manager.add_column("key", "varchar(100)", "")
        manager.add_column("value", "text", "")
        manager.add_index("key")


def init_note_tag_bind_table():
    """笔记标签绑定
    @since 2023/05/20
    """
    table_name = "note_tag_bind"
    with create_table_manager(table_name) as manager:
        manager.add_column("ctime", "datetime", "1970-01-01 00:00:00")
        manager.add_column("mtime", "datetime", "1970-01-01 00:00:00")
        manager.add_column("user", "varchar(64)", "")
        manager.add_column("note_id", "bigint", default_value=0)
        manager.add_column("tag_name", "varchar(64)", "")
        manager.add_index(["user", "tag_name"])


def init_file_info():
    """文件信息
    @since 2023/05/26
    """
    table_name = "file_info"
    with create_table_manager(table_name) as manager:
        manager.add_column("ctime", "datetime", "1970-01-01 00:00:00")
        manager.add_column("mtime", "datetime", "1970-01-01 00:00:00")
        manager.add_column("fpath", "text", "")
        manager.add_column("ftype", "varchar(32)", "")
        manager.add_column("fsize", "bigint", 0)
        manager.add_index("fpath")
        manager.add_index(["ftype", "fpath"])


class DBPool:

    sqlite_pool = {}

    @classmethod
    def get_sqlite_db(cls, fname=""):
        assert fname != ""
        if fname in cls.sqlite_pool:
            return cls.sqlite_pool.get(fname)
        fpath = os.path.join(xconfig.FileConfig.sqlite_dir, fname)
        db = MySqliteDB(db=fpath)
        cls.sqlite_pool[fname] = db
        return db


def DBWrapper(dbpath, tablename):
    db = MySqliteDB(db=dbpath)
    return TableProxy(db, tablename)


def get_file_table():
    return get_table_by_name("file")


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
    return get_table_by_name("user")


def get_message_table():
    return get_table_by_name("message")


def get_record_table():
    return get_table_by_name("record")


def get_dict_table():
    return get_table_by_name("dictionary")


get_dictionary_table = get_dict_table


def get_file_info_table():
    return get_table_by_name("file_info")


def init_backup_table(tablename, db):
    table_info = TableManager.get_table_info(tablename)
    if table_info == None:
        raise Exception("table not defined: %s" % tablename)

    with TableManager(tablename, db=db, is_backup=True) as manager:
        for args, kw in table_info.columns:
            manager.add_column(*args, **kw)

        for args, kw in table_info.indexes:
            manager.add_index(*args, **kw)

    return TableProxy(db, tablename)


def get_table(table_name, dbpath=None):
    """获取数据库表，表的创建和访问不必在xtables中定义
    @since 2019/04/11
    """
    return get_table_by_name(table_name)


@xutils.log_init_deco("xtables")
def init():
    TableManager.clear_table_dict()
    web.db.config.debug_sql = False
    init_dict_table()
    init_record_table()
    init_user_table()
    init_file_info()
