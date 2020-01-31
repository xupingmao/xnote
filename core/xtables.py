# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/03/15
# @modified 2020/01/31 16:46:47
"""Xnote的数据库配置
    考虑到持续运行的维护，增加表结构需要非常慎重
    考虑清楚你需要的是数据还是配置，如果是配置建议通过扩展脚本配置xconfig
"""
import os
import xutils
import xconfig
import web.db
from xutils import sqlite3

class SqliteTableManager:
    """检查数据库字段，如果不存在就自动创建"""
    def __init__(self, filename, tablename, pkName=None, pkType=None, no_pk=False):
        self.filename = filename
        self.tablename = tablename
        self.db = sqlite3.connect(filename)
        if no_pk:
            # 没有主键，创建一个占位符
            sql = "CREATE TABLE IF NOT EXISTS `%s` (_id int);" % tablename
        elif pkName is None:
            # 只有integer允许AUTOINCREMENT
            sql = "CREATE TABLE IF NOT EXISTS `%s` (id integer primary key autoincrement);" % tablename
        else:
            # sqlite允许主键重复，允许空值
            sql = "CREATE TABLE IF NOT EXISTS `%s` (`%s` %s primary key);" % (tablename, pkName, pkType)
        self.execute(sql)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def execute(self, sql, silent=False):
        cursorobj = self.db.cursor()
        try:
            if not silent:
                print(sql)
            cursorobj.execute(sql)
            kv_result = []
            result = cursorobj.fetchall()
            for single in result:
                resultMap = {}
                for i, desc in enumerate(cursorobj.description):
                    name = desc[0]
                    resultMap[name] = single[i]
                kv_result.append(resultMap)
            self.db.commit()
            return kv_result
        except Exception:
            raise

    def escape(self, strval):
        strval = strval.replace("'", "''")
        return "'%s'" % strval

    def add_column(self, colname, coltype, 
            default_value = None, not_null = False):
        """添加字段，如果已经存在则跳过，名称相同类型不同抛出异常"""
        sql = "ALTER TABLE `%s` ADD COLUMN `%s` %s" % (self.tablename, colname, coltype)

        # MySQL 使用 DESC [表名]
        columns = self.execute("pragma table_info('%s')" % self.tablename, silent=True)
        # print(columns.description)
        # description结构
        for column in columns:
            name = column["name"]
            type = column["type"]
            if name == colname:
                # 已经存在
                return
        if default_value != None:
            if isinstance(default_value, str):
                default_value = self.escape(default_value)
            sql += " DEFAULT %s" % default_value
        if not_null:
            sql += " NOT NULL"
        self.execute(sql)

    def add_index(self, colname, is_unique = False):
        # sqlite的索引和table是一个级别的schema
        if isinstance(colname, list):
            idx_name = "idx_" + self.tablename
            for name in colname:
                idx_name += "_" + name
            colname_str = ",".join(colname)
            sql = "CREATE INDEX IF NOT EXISTS %s ON `%s` (%s)" % (idx_name, self.tablename, colname_str)
        else:
            sql = "CREATE INDEX IF NOT EXISTS idx_%s_%s ON `%s` (`%s`)" % (self.tablename, colname, self.tablename, colname)
        try:
            self.execute(sql)
        except Exception:
            xutils.print_exc()

    def drop_index(self, col_name):
        sql = "DROP INDEX idx_%s_%s" % (self.tablename, col_name)
        try:
            self.execute(sql)
        except Exception:
            xutils.print_exc()


    def drop_column(self, colname):
        # sql = "ALTER TABLE `%s` DROP COLUMN `%s`" % (self.tablename, colname)
        # sqlite不支持 DROP COLUMN 得使用中间表
        # TODO
        pass

    def generate_migrate_sql(self, dropped_names):
        """生成迁移字段的SQL（本质上是迁移）"""
        columns = self.execute("pragma table_info('%s')" % self.tablename, silent=True)
        new_names = []
        old_names = []
        for column in columns:
            name = column["name"]
            type = column["type"]
            old_names.append(name)
            if name not in dropped_names:
                new_names.append(name)
        # step1 = "ALTER TABLE %s RENAME TO backup_table;" % (self.tablename)
        step2 = "INSERT INTO %s (%s) \nSELECT %s FROM backup_table;" % (
                self.tablename,
                ",".join(new_names),
                ",".join(old_names)
            )
        return step2

    def close(self):
        self.db.close()

TableManager = SqliteTableManager

def init_test_table():
    """测试数据库"""
    path = os.path.join(xconfig.DATA_DIR, "test.db")
    with TableManager(path, "test") as manager:
        manager.add_column("id1", "integer", 0)
        manager.add_column("int_value", "int", 0)
        manager.add_column("float_value", "float")
        manager.add_column("text_value", "text", "")
        manager.add_column("name", "text", "test")
        manager.add_column("check", "text", "aaa'bbb")
        manager.add_index("check")

def init_file_table():
    with TableManager(xconfig.DB_PATH, "file") as manager:
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
    with TableManager(xconfig.DB_PATH, "note_content") as manager:
        # 纯文本，用于搜索
        manager.add_column("content", "text", "")
        # 原始的数据，比如带标签的HTML，还有图片等的base64数据
        manager.add_column("data", "text", "")

def init_note_history_table():
    dbpath = os.path.join(xconfig.DATA_DIR, "record.db")
    with TableManager(dbpath, "note_history") as manager:
        manager.add_column("note_id", "int", 0)
        manager.add_column("name",    "text", "")
        manager.add_column("content", "text", "")
        manager.add_column("mtime",   "text", "")
        manager.add_column("version", "int", 0)
        manager.add_index(["note_id", "version"])

def init_marked_file_table():
    # @since 2018/03/02
    with TableManager(xconfig.DB_PATH, "marked_file") as manager:
        manager.add_column("user", "text", "")
        manager.add_column("file_id", "int", 0)
        manager.add_column("name",  "text", "")
        manager.add_column("ctime", "text", "")

def init_tag_table():
    # 标签表，可以用于一些特征的标记
    # 2017/04/18
    with TableManager(xconfig.DB_PATH, "file_tag", no_pk=True) as manager:
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
    with TableManager(xconfig.DB_PATH, "schedule") as manager:
        manager.add_column("name", "text", "")
        manager.add_column("url",         "text", "")
        manager.add_column("ctime",       "text", "")
        manager.add_column("mtime",       "text", "")
        manager.add_column("tm_wday", "text", "")  # Week Day no-repeat 一次性任务
        manager.add_column("tm_hour", "text", "")
        manager.add_column("tm_min",  "text", "")
        # 任务是否生效，用于一次性活动
        manager.add_column("active", "int", 1)
        manager.add_column("creator", "text", "")
        # 2017.10.21
        manager.add_column("message", "text", "") # 提醒消息
        manager.add_column("sound", "int", 0) # 是否语音提醒
        manager.add_column("webpage", "int", 0) # 是否网页提醒


def init_history_table():
    # 2017/05/21
    dbpath = os.path.join(xconfig.DATA_DIR, "record.db")
    with TableManager(dbpath, "history") as manager:
        manager.add_column("type", "text", "")
        manager.add_column("key",  "text", "")
        manager.add_column("user", "text", "")
        manager.add_column("ctime", "text", "")
        # 耗时
        manager.add_column("rt", "int", 0)


def init_user_table():
    # 2017/05/21
    # 简单的用户表
    with TableManager(xconfig.DB_PATH, "user") as manager:
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
    with TableManager(xconfig.DB_PATH, "message") as manager:
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
    with TableManager(xconfig.DB_PATH, "collection") as manager:
        manager.add_column("user", "text", "")
        manager.add_column("name", "text", "")
        manager.add_column("link", "text", "")
        manager.add_column("type", "text", "")

def init_record_table():
    # 日志库和主库隔离开
    dbpath = os.path.join(xconfig.DATA_DIR, "record.db")
    with TableManager(dbpath, "record") as manager:
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
    with TableManager(dbpath, "storage") as manager:
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
    with TableManager(dbpath, "dictionary") as manager:
        manager.add_column("ctime", "text", "")
        manager.add_column("mtime", "text", "")
        manager.add_column("user",  "text", "")
        manager.add_column("key", "text", "")
        manager.add_column("value", "text", "")
        manager.add_index("key")

def init_search_rule_table():
    """搜索规则（智能文件夹）
    @since 2019/02/18
    """
    with TableManager(xconfig.DB_PATH, "search_rule") as manager:
        manager.add_column("ctime", "text", "")
        manager.add_column("mtime", "text", "")
        manager.add_column("user",  "text", "")
        manager.add_column("name", "text", "")
        manager.add_column("expression", "text", "")
        manager.add_index("user")

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

class DBWrapper:
    """基于web.db的装饰器
    SqliteDB是全局唯一的，它的底层使用了连接池技术，每个线程都有独立的sqlite连接
    """

    _pool = dict()

    def __init__(self, dbpath, tablename):
        self.tablename = tablename
        self.dbpath = dbpath
        # SqliteDB 内部使用了threadlocal来实现，是线程安全的，使用全局单实例即可
        _db = DBWrapper._pool.get(dbpath)
        if xutils.sqlite3 is None:
            self.db = MockedDB()
            return
        if _db is None:
            raise Exception("db wrapper %s is not inited!" % dbpath)
        self.db = _db

    def insert(self, *args, **kw):
        return self.db.insert(self.tablename, *args, **kw)

    def select(self, *args, **kw):
        return self.db.select(self.tablename, *args, **kw)

    def select_first(self, *args, **kw):
        return self.db.select(self.tablename, *args, **kw).first()

    def query(self, *args, **kw):
        return self.db.query(*args, **kw)

    def count(self, where=None, sql = None, vars = None):
        if sqlite3 is None:
            return 0
        if sql is None:
            if isinstance(where, dict):
                return self.select_first(what = "COUNT(1) AS amount", where = where).amount
            else:
                sql = "SELECT COUNT(1) AS amount FROM %s" % self.tablename
                if where:
                    sql += " WHERE %s" % where
        return self.db.query(sql, vars = vars).first().amount

    def update(self, *args, **kw):
        return self.db.update(self.tablename, *args, **kw)

    def delete(self, *args, **kw):
        return self.db.delete(self.tablename, *args, **kw)

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
    return DBWrapper(xconfig.DICT_FILE, "dictionary")

def get_search_rule_table():
    return DBWrapper(xconfig.DB_PATH, "search_rule")


get_dictionary_table = get_dict_table

def get_table(name, dbpath = None):
    """获取数据库表，表的创建和访问不必在xtables中定义
    @since 2019/04/11
    """
    if dbpath is None:
        dbpath = xconfig.DB_FILE
    return DBWrapper(dbpath, name)

def init_db_wrapper(dbpath):
    db = web.db.SqliteDB(db = dbpath)
    db.query("PRAGMA temp_store = MEMORY;")
    # 启用Memory-Mapped I/O
    db.query("PRAGMA mmap_size=268435456;")
    db.query("PRAGMA synchronous = NORMAL;")
    DBWrapper._pool[dbpath] = db

def init():
    if sqlite3 is None:
        xconfig.errors.append("sqlite3依赖丢失,部分功能不可用")
        return

    # init_db_wrapper(xconfig.DB_FILE)
    init_db_wrapper(xconfig.DICT_FILE)
    # init_db_wrapper(xconfig.RECORD_FILE)

    # init_user_table()
    # init_file_table()
    # init_tag_table()
    # init_note_content_table()
    # init_note_history_table()

    # init_schedule_table()
    # init_message_table()
    init_dict_table()
    # init_storage_table()
    # init_collection_table()
    # init_search_rule_table()
    # 非核心结构记录各种日志数据
    # init_record_table()

