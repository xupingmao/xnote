# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-04-28 20:36:45
@LastEditors  : xupingmao
@LastEditTime : 2024-06-22 23:02:47
@FilePath     : /xnote/xutils/sqldb/table_manager.py
@Description  : SQL表结构管理
"""

import re
import logging
import xutils
import typing
import web.db
from .table_config import TableConfig
from xutils.functions import list_replace

empty_db = web.db.DB(None, {})

class ColumnInfo:
    def __init__(self):
        self.name = ""
        self.type = ""

def quote_name(name: str):
    if "`" in name:
        return name
    return f"`{name}`"

class TableHelper:

    def __init__(self, quote="`", skip_prefix_length = False):
        self.quote = quote
        self.skip_prefix_length = skip_prefix_length

    def quote_col(self, colname=""):
        if self.quote in colname:
            return colname
    
        if "(" in colname:
            # like field_name(10)
            colname = colname.replace(")", "")
            colname = colname.replace("(", " ")
            colname, length = colname.split()
            if self.skip_prefix_length:
                return f"{self.quote}{colname}{self.quote}"
            return f"{self.quote}{colname}{self.quote}({length})"
        
        return f"{self.quote}{colname}{self.quote}"
    
    @classmethod
    def _do_single_name(cls, colname: str):
        if "(" in colname:
            # like field_name(10)
            return colname.split("(")[0]
        return colname

    def to_colname_only(self, colname):
        if isinstance(colname, list):
            return [self._do_single_name(x) for x in colname]
        return self._do_single_name(colname)

    def build_index_name(self, colname, is_unique=False, table_name=""):
        colname = self.to_colname_only(colname)
        index_prefix = "idx"
        if is_unique:
            index_prefix = "uk"

        if table_name != "":
            index_prefix += f"_{table_name}"

        if isinstance(colname, list):
            colname_list = "_".join(colname)
            return f"{index_prefix}_{colname_list}"
        else:
            return f"{index_prefix}_{colname}"

    def build_colname_tuple(self, colname):
        if isinstance(colname, list):
            col_list = [self.quote_col(x) for x in colname]
            return ",".join(col_list)
        else:
            return self.quote_col(colname)
        
    @classmethod
    def get_type_name(cls, type_name: str):
        """获取字段的类型名称,不包含长度"""
        return cls._do_single_name(type_name)

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
        self.pk_len = kw.get("pk_len", 0) # 废弃字段
        self.pk_comment = kw.get("pk_comment", "主键")
        pk_type = TableHelper.get_type_name(self.pk_type)
        # 目前只支持这两种主键
        assert pk_type in ("int", "varbinary")

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

    def escape(self, strval: str):
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

    def rename_column(self, old_name="", new_name=""):
        columns = self.desc_columns()
        names = [col.name for col in columns]
        if new_name in names:
            return
        if old_name not in names:
            return
        sql = f"ALTER TABLE {self.tablename} RENAME {quote_name(old_name)} TO {quote_name(new_name)}"
        self.execute(sql)

    def add_index(self, colname, is_unique=False, **kw):
        raise Exception("not implemented")

    def drop_index(self, col_name, is_unique=False):
        raise Exception("not implemented")

    def drop_column(self, colname):
        sql = "ALTER TABLE `%s` DROP COLUMN `%s`" % (self.tablename, colname)
        self.execute(sql)

    def close(self):
        pass

    
    def quote_col(self, colname=""):
        return quote_name(colname)

class MySQLTableManager(BaseTableManager):
    # TODO 待实现测试

    def connect(self):
        pass

    def create_table(self):
        table_name = self.tablename
        pk_name = self.pk_name
        pk_comment = self.pk_comment
        if self.pk_type == "blob":
            # MySQL的blob不能作为主键,需要转换成 varbinary
            self.pk_type = "varbinary(100)"
        
        if self.pk_type == "int":
            sql = f"""CREATE TABLE IF NOT EXISTS `{table_name}` (
                `{pk_name}` bigint unsigned not null auto_increment,
                PRIMARY KEY (`{pk_name}`)
            ) CHARACTER SET utf8mb4;"""
        else:
            sql = f"""CREATE TABLE IF NOT EXISTS `{table_name}` (
                `{pk_name}` {self.pk_type} not null,
                PRIMARY KEY (`{pk_name}`)
            ) CHARACTER SET utf8mb4;"""
        self.db.query(sql)

    
    def desc_columns(self):
        sql = f"DESC `{self.tablename}`"
        columns = list(self.db.query(sql)) # type: ignore
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
        if coltype in ("text", "blob", "longblob"):
            # MySQL5.7不支持默认值
            default_value = None
        super().add_column(colname, coltype, default_value, not_null)
    
    def add_index(self, colname, is_unique=False, **kw):
        """MySQL版创建索引"""
        helper = TableHelper()
        index_name = helper.build_index_name(colname=colname, is_unique=is_unique)
        colname_str = helper.build_colname_tuple(colname=colname)

        if is_unique:
            sql = f"ALTER TABLE `{self.tablename}` ADD UNIQUE `{index_name}` ({colname_str})"
        else:
            sql = f"ALTER TABLE `{self.tablename}` ADD INDEX `{index_name}` ({colname_str})"

        if self.is_index_exists(index_name):
            logging.info("index %s already exists", index_name)
            return
        
        logging.info("%s", sql)
        if not TableConfig.enable_auto_ddl:
            raise Exception("db_auto_ddl is disabled")
        self.execute(sql)

    def drop_index(self, col_name, is_unique=False):
        # return super().drop_index(col_name, is_unique)
        helper = TableHelper()
        index_name = helper.build_index_name(colname=col_name, is_unique=is_unique)
        if self.is_index_exists(index_name):
            sql = f"ALTER TABLE `{self.tablename}` DROP INDEX {index_name}"
            self.execute(sql)
    
    def is_index_exists(self, index_name=""):
        assert len(self.mysql_database) > 0
        sql = "SELECT COUNT(*) as amount FROM information_schema.statistics WHERE table_schema=$database AND table_name = $table_name AND index_name = $index_name"
        vars = dict(database=self.mysql_database, table_name=self.tablename, index_name=index_name)
        first = self.db.query(sql, vars=vars).first() # type: ignore
        return first.amount > 0 # type:ignore
    

class SqliteTableManager(BaseTableManager):

    def connect(self):
        pass

    def create_table(self):
        table_name = self.tablename
        pk_name = self.pk_name

        if self.pk_type == "int":
            sql = f"""CREATE TABLE IF NOT EXISTS `{table_name}`(
                {pk_name} integer primary key autoincrement
            );"""
        else:
            sql = f"""CREATE TABLE IF NOT EXISTS `{table_name}` (
                {pk_name} {self.pk_type} primary key
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
        for column in columns: # type:ignore
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
        # Update: 新版已经支持了
        pass

    def desc_columns(self):
        columns = self.execute(f"pragma table_info('{self.tablename}')")
        result = []
        for col in columns: # type:ignore
            item = ColumnInfo()
            item.type = col["type"]
            item.name = col["name"]
            result.append(item)
        return result

    def add_index(self, colname, is_unique=False, **kw):
        # sqlite的索引和table是一个级别的schema
        # sqlite不支持前缀索引
        helper = TableHelper(skip_prefix_length=True)
        idx_name = helper.build_index_name(colname=colname, is_unique=is_unique, table_name=self.tablename)
        colname_str = helper.build_colname_tuple(colname=colname)
                            
        if is_unique:
            sql = f"CREATE UNIQUE INDEX IF NOT EXISTS {idx_name} ON `{self.tablename}` ({colname_str})"
        else:
            sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON `{self.tablename}` ({colname_str})"
            
        self.execute(sql)

    def drop_index(self, col_name, is_unique=False):
        helper = TableHelper()
        index_name = helper.build_index_name(colname=col_name, is_unique=is_unique, table_name=self.tablename)
        sql = f"DROP INDEX IF EXISTS {index_name}"
        self.execute(sql)

class ColumnDef:
    def __init__(self, name: str, args, kw: dict):
        self.name = name
        self.args = args
        self.kw = kw

class TableInfo:

    def __init__(self, tablename = ""):
        self.tablename = tablename
        self.pk_name = "id"
        self.db_type = "" # 数据库类型, 比如 mysql/sqlite
        self.comment = "" # 表的描述
        self.column_names = []
        self.columns = [] # type:list[ColumnDef] # 这个主要用于记录[args, kw]参数用于复制表结构
        self.indexes = [] # 这个主要用于记录[args, kw]参数用于复制表结构
        self.dbpath = "" # sqlite文件路径
        self.enable_binlog = True
        self.log_profile = True
        self.is_deleted = False
    
    def add_column(self, colname, *args, **kw):
        self.column_names.append(colname)
        column_def = ColumnDef(colname, args, kw)
        self.columns.append(column_def)

    def rename_column(self, old_name: str, new_name:str):
        self.column_names = list_replace(self.column_names, old_name, new_name)
        for column in self.columns:
            if column.name == old_name:
                column.name = new_name
    
    def add_index(self, *args, **kw):
        self.indexes.append([args, kw])

    def get_column_comment(self, colname=""):
        for info in self.columns:
            if info.name == colname:
                return info.kw.get("comment", "")
        return ""

class TableManagerFacade:

    table_dict = {} # type: dict[str, TableInfo]

    def __init__(self, tablename, db = empty_db, is_backup = False, **kw):
        self.table_info = TableInfo(tablename)
        self.table_info.pk_name = kw.get("pk_name", "id")
        self.table_info.db_type = kw.get("db_type", "")
        if db.dbname == "mysql":
            self.manager = MySQLTableManager(tablename, db = db, **kw)
        else:
            dbpath = kw.get("dbpath", "")
            assert dbpath != "", "sqlite dbpath is empty"
            self.manager = SqliteTableManager(tablename, db = db, **kw)
            self.table_info.dbpath = dbpath
        
        self.table_info.is_deleted = kw.get("is_deleted", False)
        self.table_info.comment = kw.get("comment", "")

        self.manager.create_table()

        check_table_define = kw.get("check_table_define", True)
        if not is_backup and check_table_define:
            if tablename in self.table_dict:
                raise Exception("table already defined: %s" % tablename)
        
        if not is_backup:
            self.table_dict[tablename] = self.table_info
    
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

    def add_column(self, colname, coltype: str,
                   default_value=None, not_null=True, comment="", 
                   old_names:typing.List[str]=[]):
        """Check and add column, do nothing if column exists.
        Args:
            - colname: column name
            - coltype: column type
            - default_value: default value
            - not_null: not null constriants
            - comment: comment
            - old_names: if old_names is passed, rename old column names to new column name.
        """
        for old_name in old_names:
            self.rename_column(old_name=old_name, new_name=colname)

        coltype_lower = coltype.lower()

        if "varchar" in coltype_lower:
            assert default_value != None, f"varchar column {colname} default value cant be NULL"
        if coltype_lower in ("int", "tinyint", "bigint"):
            assert default_value != None, f"{coltype} column {colname} default value cant be NULL"
        
        self.table_info.add_column(colname, coltype, default_value, not_null, comment=comment)
        self.manager.add_column(colname, coltype, default_value, not_null, comment=comment)

    def rename_column(self, old_name: str, new_name: str):
        """Rename column. do nothing if old_name not exists or new_name exists.
        """
        self.table_info.rename_column(old_name, new_name)
        self.manager.rename_column(old_name, new_name)
    
    def drop_column(self, colname, coltype,
                   default_value=None, not_null=True):
        """只会打一个告警日志,不会实际删除,删除字段请使用rename_column或者重建表,更加安全"""
        logging.warning(f"drop column {colname}")

    def add_index(self, colname, is_unique=False, **kw):
        self.table_info.add_index(colname, is_unique)
        self.manager.add_index(colname, is_unique, **kw)

    def drop_index(self, colname, is_unique=False, **kw):
        self.manager.drop_index(colname, is_unique, **kw)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.manager.close()