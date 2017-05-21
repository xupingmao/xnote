# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/03/15
# 

"""Xnote的数据库配置"""

import sqlite3
import config

class SqliteTableManager:
    """检查数据库字段，如果不存在就自动创建"""
    def __init__(self, filename, tablename):
        self.filename = filename
        self.tablename = tablename
        self.db = sqlite3.connect(filename)
        sql = "CREATE TABLE IF NOT EXISTS `%s` (id bigint primary key autoincrement);" % tablename
        self.execute(sql)

    def execute(self, sql):
        cursorobj = self.db.cursor()
        try:
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
        columns = self.execute("pragma table_info('%s')" % self.tablename)
        # print(columns.description)
        # description结构
        # ()
        for column in columns:
            name = column["name"]
            type = column["type"]
            if name == colname and type == coltype:
                # 已经存在
                return
        if default_value != None:
            if isinstance(default_value, str):
                default_value = self.escape(default_value)
            sql += " DEFAULT %s" % default_value
        if not_null:
            sql += " NOT NULL"
        self.execute(sql)

    def close(self):
        self.db.close()

TableManager = SqliteTableManager

def init_table_test():
    TEST_DB = "db/test.db"
    manager = TableManager("db/test.db", "test")

    manager.add_column("id1", "integer", 0)
    manager.add_column("int_value", "int", 0)
    manager.add_column("float_value", "float")
    manager.add_column("text_value", "text", "")
    manager.add_column("name", "text", "test")
    manager.add_column("check", "text", "aaa'bbb")
    manager.close()
    # import sys
    # sys.exit(0)

def init_table_file():
    manager = TableManager(config.DB_PATH, "file")
    manager.add_column("name", "text", "")
    manager.add_column("content", "text", "")
    manager.add_column("size", "long", 0)
    # 类型, markdown, post, mailist, file
    # 类型为file时，content值为文件的web路径
    manager.add_column("type", "text", "")
    
    # 关联关系
    # 上级目录
    manager.add_column("parent_id", "int", 0)
    manager.add_column("related", "text", "")

    # 统计相关
    # 访问次数
    # 创建时间ctime
    manager.add_column("sctime", "text", "")
    # 修改时间mtime
    manager.add_column("smtime", "text", "")
    # 访问时间atime
    manager.add_column("satime", "text", "")
    manager.add_column("visited_cnt", "int", 0)
    manager.add_column("is_deleted", "int", 0)

    # 权限相关
    # 创建者
    manager.add_column("creator", "text", "")
    # 修改者
    manager.add_column("modifier", "text", "")
    manager.add_column("groups", "text", "")
    
    # MD5
    manager.add_column("md5", "text", "")
    # 修改版本
    manager.add_column("version", "int", 0)
    manager.close()

def init_table_tag():
    # 2017/04/18
    manager = TableManager(config.DB_PATH, "file_tag")
    # 标签名
    manager.add_column("name",    "text", "")
    # 标签ID
    manager.add_column("file_id", "int", 0)
    # 权限控制
    manager.add_column("groups",  "text", "")
    manager.close()

def init_table_log():
    # 2017/05/21
    manager = TableManager(config.LOG_PATH, "xnote_log")
    manager.add_column("tag",      "text", "")
    manager.add_column("operator", "text", "")

def init():
    # init_test_db()
    init_table_file()
    init_table_tag()

