# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-04-28 20:36:45
@LastEditors  : xupingmao
@LastEditTime : 2024-04-05 11:58:25
@FilePath     : /xnote/xutils/sqldb/table_manager.py
@Description  : SQL表结构管理
"""

import logging
import xutils
import web.db
from .table_config import TableConfig

empty_db = web.db.DB(None, {})

class ColumnInfo:

    def __init__(self):
        self.name = ""
        self.type = ""

class BaseTableManager:
    """检查数据库字段，如果不存在就自动创建"""

    def __init__(self, tablename, db = empty_db, **kw):
        self.tablename = tablename
        self.kw = kw
        self.debug = kw.pop("debug", False)
        self.connect()
        self.db = db
        self.mysql_database = kw.get("mysql_database", "")
        self.pk_name = kw.get("pk_name", "id")
        self.pk_type = kw.get("pk_type", "int")
        self.pk_len = kw.get("pk_len", 0)
        self.pk_comment = kw.get("pk_comment", "主键")
        # 目前只支持这两种主键
        assert self.pk_type in ("int", "blob")

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def create_table(self):
        if self.db.dbname == "sqlite":
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
                   default_value=None, not_null=True, **kw):
        """添加字段，如果已经存在则跳过，名称相同类型不同抛出异常"""
        sql = f"ALTER TABLE `{self.tablename}` ADD COLUMN `{colname}` {coltype}"
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

    def add_index(self, colname, is_unique=False, **kw):
        raise Exception("not implemented")

    def drop_index(self, col_name, is_unique=False):
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

    
    def quote_col(self, colname=""):
        if "`" in colname:
            return colname
        return "`%s`" % colname

class MySQLTableManager(BaseTableManager):
    # TODO 待实现测试

    def connect(self):
        pass

    def create_table(self):
        table_name = self.tablename
        pk_name = self.pk_name
        pk_len = self.pk_len
        pk_comment = self.pk_comment
        if self.pk_type == "blob":
            sql = f"""CREATE TABLE IF NOT EXISTS `{table_name}` (
                `{pk_name}` blob not null comment '{pk_comment}',
                PRIMARY KEY (`{pk_name}`({pk_len}))
            )"""
        else:
            sql = f"""CREATE TABLE IF NOT EXISTS `{table_name}` (
                `{pk_name}` bigint unsigned not null auto_increment,
                PRIMARY KEY (`{pk_name}`)
            ) CHARACTER SET utf8mb4;"""
        self.db.query(sql)

    
    def desc_columns(self):
        sql = "DESC `%s`" % self.tablename
        columns = list(self.db.query(sql))
        if self.debug:
            print("desc %s, columns=%s" % (self.tablename, columns))
        result = []
        for col in columns:
            item = ColumnInfo()
            item.type = col["Type"]
            item.name = col["Field"]
            result.append(item)
        return result
    
    def execute(self, sql):
        return self.db.query(sql)
    
    def add_column(self, colname, coltype,
                   default_value=None, not_null=True, **kw):
        if coltype == "text":
            # MySQL5.7不支持默认值
            default_value = None
        super().add_column(colname, coltype, default_value, not_null)
    
    def add_index(self, colname, is_unique=False, key_len=0, key_len_list=[], **kw):
        """MySQL版创建索引"""
        index_name = ""
        colname_str = ""

        index_prefix = "idx"
        if is_unique:
            index_prefix = "uk"

        if isinstance(colname, list):
            index_name = index_prefix
            for name in colname:
                index_name += "_" + name
            temp_col_list = []
            for index, name in enumerate(colname):
                if index < len(key_len_list):
                    key_len = key_len_list[index]
                else:
                    key_len = 0
                if key_len > 0:
                    tmp_col_name = self.quote_col(name) + "(%d)" % key_len
                else:
                    tmp_col_name = self.quote_col(name)
                temp_col_list.append(tmp_col_name)
            colname_str = ",".join(temp_col_list)
        else:
            index_name = index_prefix + "_" + colname
            colname_str = self.quote_col(colname)
            if key_len > 0:
                colname_str += "(%d)" % key_len

        if is_unique:
            sql = "ALTER TABLE `%s` ADD UNIQUE `%s` (%s)" % (
                    self.tablename, index_name, colname_str)
        else:
            sql = "ALTER TABLE `%s` ADD INDEX `%s` (%s)" % (
                    self.tablename, index_name, colname_str)

        if self.is_index_exists(index_name):
            logging.info("index %s already exists", index_name)
            return
        
        logging.info("%s", sql)
        if not TableConfig.enable_auto_ddl:
            raise Exception("db_auto_ddl is disabled")
        self.execute(sql)
        
    
    def is_index_exists(self, index_name=""):
        assert len(self.mysql_database) > 0
        sql = "SELECT COUNT(*) as amount FROM information_schema.statistics WHERE table_schema=$database AND table_name = $table_name AND index_name = $index_name"
        first = self.db.query(sql, vars=dict(database=self.mysql_database, table_name=self.tablename, index_name=index_name)).first()
        return first.amount > 0
    

class SqliteTableManager(BaseTableManager):

    def connect(self):
        pass

    def create_table(self):
        table_name = self.tablename
        pk_name = self.pk_name

        if self.pk_type == "blob":
            sql = f"""CREATE TABLE IF NOT EXISTS `{table_name}` (
                {pk_name} blob primary key
            );"""
        else:
            sql = f"""CREATE TABLE IF NOT EXISTS `{table_name}`(
                {pk_name} integer primary key autoincrement
            );"""
        self.execute(sql)

    def execute(self, sql):
        try:
            if self.debug:
                logging.debug(sql)
            return self.db.query(sql)
        except Exception as e:
            raise e

    def close(self):
        pass

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
    
    def add_column(self, colname, coltype,
                   default_value=None, not_null=True, **kw):
        if coltype == "text" and default_value == None:
            default_value = ""
        super().add_column(colname, coltype, default_value, not_null)

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

    def add_index(self, colname, is_unique=False, **kw):
        # sqlite的索引和table是一个级别的schema
        index_prefix = "idx_"
        if is_unique:
            index_prefix = "uk_"

        colname_str = colname
        
        if isinstance(colname, list):
            idx_name = index_prefix + self.tablename + "_" + "_".join(colname)
            colname_str = ",".join(colname)
        else:
            idx_name = index_prefix + self.tablename + "_" + colname
                            
        if is_unique:
            sql = "CREATE UNIQUE INDEX IF NOT EXISTS %s ON `%s` (%s)" % (
                idx_name, self.tablename, colname_str)
        else:
            sql = "CREATE INDEX IF NOT EXISTS %s ON `%s` (%s)" % (
                idx_name, self.tablename, colname_str)
            
        self.execute(sql)

class TableInfo:

    def __init__(self, tablename = ""):
        self.tablename = tablename
        self.pk_name = "id"
        self.db_type = "" # 数据库类型, 比如 mysql/sqlite
        self.comment = "" # 表的描述
        self.column_names = []
        self.columns = []
        self.indexes = []
        self.dbpath = "" # sqlite文件路径
        self.enable_binlog = True
        self.log_profile = True
        self.is_deleted = False
    
    def add_column(self, colname, *args, **kw):
        self.column_names.append(colname)
        self.columns.append([(colname, ) + args, kw])
    
    def add_index(self, *args, **kw):
        self.indexes.append([args, kw])

class TableManagerFacade:

    table_dict = {}

    @classmethod
    def clear_table_dict(cls):
        cls.table_dict = {}
    
    @classmethod
    def get_table_info(cls, tablename=""):
        # type: (str) -> TableInfo|None
        return cls.table_dict.get(tablename)
    
    @classmethod
    def get_table_info_dict(cls):
        # type: () -> dict[str, TableInfo]
        return cls.table_dict

    def __init__(self, tablename, db = empty_db, is_backup = False, **kw):
        self.table_info = TableInfo(tablename)
        self.table_info.pk_name = kw.get("pk_name", "id")
        self.table_info.db_type = kw.get("db_type", "")
        if db.dbname == "mysql":
            self.manager = MySQLTableManager(tablename, db = db, **kw)
        else:
            self.manager = SqliteTableManager(tablename, db = db, **kw)
            self.table_info.dbpath = db.dbpath
        
        self.table_info.is_deleted = kw.get("is_deleted", False)
        self.table_info.comment = kw.get("comment", "")

        self.manager.create_table()

        check_table_define = kw.get("check_table_define", True)
        if not is_backup and check_table_define:
            if tablename in self.table_dict:
                raise Exception("table already defined: %s" % tablename)
        
        if not is_backup:
            self.table_dict[tablename] = self.table_info
    
    def add_column(self, colname, coltype,
                   default_value=None, not_null=True, comment=""):
        coltype_lower = coltype.lower()

        if "varchar" in coltype_lower:
            assert default_value != None, f"varchar column {colname} default value cant be NULL"
        if coltype_lower in ("int", "tinyint", "bigint"):
            assert default_value != None, f"{coltype} column {colname} default value cant be NULL"
        
        self.table_info.add_column(colname, coltype, default_value, not_null)
        self.manager.add_column(colname, coltype, default_value, not_null, comment=comment)
    
    def drop_column(self, colname, coltype,
                   default_value=None, not_null=True):
        pass

    def add_index(self, colname, is_unique=False, **kw):
        self.table_info.add_index(colname, is_unique)
        self.manager.add_index(colname, is_unique, **kw)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.manager.close()