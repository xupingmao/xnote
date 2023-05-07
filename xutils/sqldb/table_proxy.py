# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-04-28 21:09:40
@LastEditors  : xupingmao
@LastEditTime : 2023-05-07 17:06:38
@FilePath     : /xnote/xutils/sqldb/table_proxy.py
@Description  : 描述
"""


class TableProxy:
    """基于web.db的装饰器
    SqliteDB是全局唯一的，它的底层使用了连接池技术，每个线程都有独立的sqlite连接
    """

    def __init__(self, db, tablename):
        self.tablename = tablename
        # SqliteDB 内部使用了threadlocal来实现，是线程安全的，使用全局单实例即可
        self.db = db

    def fix_sql_keywords(self, where):
        # 兼容关键字
        if isinstance(where, dict):
            key = where.pop("key", None)
            if key != None:
                where["`key`"] = key

    def insert(self, seqname=None, _test=False, **values):
        self.fix_sql_keywords(values)
        # TODO 记录binlog
        return self.db.insert(self.tablename, seqname, _test, **values)

    def select(self, vars=None, what='*', where=None, order=None, group=None,
               limit=None, offset=None, _test=False):
        self.fix_sql_keywords(where)
        return self.db.select(self.tablename, vars=vars, what=what, where=where, order=order, group=group,
                              limit=limit, offset=offset, _test=_test)

    def select_first(self, *args, **kw):
        return self.select(self.tablename, *args, **kw).first()

    def query(self, *args, **kw):
        return self.db.query(*args, **kw)

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

