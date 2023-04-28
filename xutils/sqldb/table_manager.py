# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-04-28 20:36:45
@LastEditors  : xupingmao
@LastEditTime : 2023-04-28 21:54:22
@FilePath     : /xnote/xutils/sqldb/table_manager.py
@Description  : 描述
"""

import sqlite3
import xutils


class ColumnInfo:

    def __init__(self):
        self.name = ""
        self.type = ""

class BaseTableManager:
    """检查数据库字段，如果不存在就自动创建"""

    def __init__(self, tablename, pkName=None, pkType=None, no_pk=False, **kw):
        self.tablename = tablename
        self.kw = kw
        self.pk_name = pkName
        self.pk_type = pkType
        self.no_pk = no_pk
        self.debug = kw.pop("debug", False)
        self.connect()
        self.create_table()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def create_table(self):
        pass

    def connect(self):
        pass

    def execute(self, sql):
        pass

    def escape(self, strval):
        strval = strval.replace("'", "''")
        return "'%s'" % strval
    
    def desc_columns(self):
        demo = ColumnInfo()
        demo.name = "demo"
        demo.type = "text"
        return [demo]

    def add_column(self, colname, coltype,
                   default_value=None, not_null=False):
        """添加字段，如果已经存在则跳过，名称相同类型不同抛出异常"""
        sql = "ALTER TABLE `%s` ADD COLUMN `%s` %s" % (
            self.tablename, colname, coltype)
        
        columns = self.desc_columns()
        for column in columns:
            name = column.name
            type = column.type
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

    def add_index(self, colname, is_unique=False):
        # sqlite的索引和table是一个级别的schema
        if isinstance(colname, list):
            idx_name = "idx_" + self.tablename
            for name in colname:
                idx_name += "_" + name
            colname_str = ",".join(colname)
            sql = "CREATE INDEX IF NOT EXISTS %s ON `%s` (%s)" % (
                idx_name, self.tablename, colname_str)
        else:
            sql = "CREATE INDEX IF NOT EXISTS idx_%s_%s ON `%s` (`%s`)" % (
                self.tablename, colname, self.tablename, colname)
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
        sql = "ALTER TABLE `%s` DROP COLUMN `%s`" % (self.tablename, colname)
        self.execute(sql)

    def close(self):
        pass


class MySQLTableManager(BaseTableManager):
    # TODO 待实现测试

    def connect(self):
        import pymysql
        pymysql.connect()

    def desc_columns(self):
        sql = "DESC `%s`" % self.tablename
        return self.execute(sql)

class SqliteTableManager(BaseTableManager):

    def connect(self):
        dbpath = self.kw.get("dbpath")
        assert isinstance(dbpath, str)
        self.db = sqlite3.connect(dbpath)

    def create_table(self):
        no_pk = self.no_pk
        tablename = self.tablename
        pkName = self.pk_name
        pkType = self.pk_type
        
        if no_pk:
            # 没有主键，创建一个占位符
            sql = "CREATE TABLE IF NOT EXISTS `%s` (_id int);" % tablename
        elif pkName is None:
            # 只有integer允许AUTOINCREMENT
            sql = "CREATE TABLE IF NOT EXISTS `%s` (id integer primary key autoincrement);" % tablename
        else:
            # sqlite允许主键重复，允许空值
            sql = "CREATE TABLE IF NOT EXISTS `%s` (`%s` %s primary key);" % (
                tablename, pkName, pkType)
        self.execute(sql)

    def execute(self, sql):
        cursorobj = self.db.cursor()
        try:
            if self.debug:
                xutils.log(sql)
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

    def close(self):
        self.db.close()

    def generate_migrate_sql(self, dropped_names):
        """生成迁移字段的SQL（本质上是迁移）"""
        columns = self.execute("pragma table_info('%s')" % self.tablename)
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
    
    def drop_column(self, colname):
        # sqlite不支持 DROP COLUMN 得使用中间表
        pass

    def desc_columns(self):
        columns = self.execute("pragma table_info('%s')" %
                        self.tablename)
        result = []
        for col in columns:
            item = ColumnInfo()
            item.type = col["type"]
            item.name = col["name"]
            result.append(item)
        return result