# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-04-28 21:09:40
@LastEditors  : xupingmao
@LastEditTime : 2023-05-24 00:13:07
@FilePath     : /xnote/xutils/sqldb/table_proxy.py
@Description  : 描述
"""

from . import table_manager

class TableProxy:
    """基于web.db的装饰器
    SqliteDB是全局唯一的，它的底层使用了连接池技术，每个线程都有独立的sqlite连接
    """

    def __init__(self, db, tablename):
        self.tablename = tablename
        # SqliteDB 内部使用了threadlocal来实现，是线程安全的，使用全局单实例即可
        self.db = db
        self.table_info = None

    def fix_sql_keywords(self, where):
        # 兼容关键字
        if isinstance(where, dict):
            key = where.pop("key", None)
            if key != None:
                where["`key`"] = key
    
    def handle_result_set(self, result_set):
        # TODO 转换类型用于序列化
        result = []
        for item in result_set:
            # for attr in item:
            #     value = item.get(attr)
            result.append(item)
        return result

    def insert(self, seqname=None, _test=False, **values):
        self.fix_sql_keywords(values)
        # TODO 记录binlog
        return self.db.insert(self.tablename, seqname, _test, **values)
    
    def _multiple_insert(self, values, seqname=None, _test=False):
        # sqlite不支持
        for value in values:
            self.fix_sql_keywords(value)
        # TODO 记录binlog
        return self.db.multiple_insert(self.tablename, values, seqname, _test)

    def select(self, vars=None, what='*', where=None, order=None, group=None,
               limit=None, offset=None, _test=False):
        self.fix_sql_keywords(where)
        result_set = self.db.select(self.tablename, vars=vars, what=what, where=where, order=order, group=group,
                              limit=limit, offset=offset, _test=_test)
        records = list(result_set)
        return records

    def select_first(self, *args, **kw):
        records = self.select(self.tablename, *args, **kw)
        if len(records) > 0:
            return records[0]
        return None

    def query(self, *args, **kw):
        return list(self.db.query(*args, **kw))

    def count(self, where=None, sql=None, vars=None):
        self.fix_sql_keywords(where)
        if sql is None:
            if isinstance(where, dict):
                return self.select_first(what="COUNT(1) AS amount", where=where).amount
            else:
                sql = "SELECT COUNT(1) AS amount FROM %s" % self.tablename
                if where:
                    sql += " WHERE %s" % where
        return self.db.query(sql, vars=vars).first().amount

    def update(self, where, vars=None, _test=False, **values):
        self.fix_sql_keywords(where)
        # TODO 记录binlog
        return self.db.update(self.tablename, where, vars=vars, _test=_test, **values)

    def delete(self,  where, using=None, vars=None, _test=False):
        self.fix_sql_keywords(where)
        # TODO 记录binlog
        return self.db.delete(self.tablename, where, using=using, vars=vars, _test=_test)
    
    def transaction(self):
        return self.db.transaction()
    
    def iter(self):
        for records in self.iter_batch():
            for record in records:
                yield record


    def iter_batch(self, batch_size=20):
        last_id = 0
        while True:
            records = self.select(where = "id > $last_id", vars = dict(last_id = last_id), limit = batch_size, order="id")
            if len(records) == 0:
                break
            yield records
            last_id = records[-1].id
    
    def get_table_info(self):
        if self.table_info == None:
            self.table_info = table_manager.TableManagerFacade.get_table_info(self.tablename)
        return self.table_info

    def filter_record(self, record):
        # type: (dict) -> dict
        result = {}
        table_info = self.get_table_info()
        for colname in table_info.column_names:
            col_value = record.get(colname)
            if col_value != None:
                result[colname] = col_value
        return result
