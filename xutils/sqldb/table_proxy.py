# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-04-28 21:09:40
@LastEditors  : xupingmao
@LastEditTime : 2023-09-23 10:24:13
@FilePath     : /xnote/xutils/sqldb/table_proxy.py
@Description  : 描述
"""
import time
import xutils
import web.db
from . import table_manager
from xutils.interfaces import ProfileLog, ProfileLogger
from xutils.db.binlog import BinLog, BinLogOpType


class TableConfig:

    log_profile = False
    enable_binlog = False

class TableProxy:
    """基于web.db的装饰器
    SqliteDB是全局唯一的, 它的底层使用了连接池技术, 每个线程都有独立的sqlite连接
    """
    log_profile = False
    enable_binlog = False
    profile_logger = ProfileLogger()

    def __init__(self, db, tablename):
        self.tablename = tablename
        # SqliteDB 内部使用了threadlocal来实现，是线程安全的，使用全局单实例即可
        assert isinstance(db, web.db.DB)
        self.db = db
        table_info = table_manager.TableManagerFacade.get_table_info(tablename)
        assert table_info != None
        self.table_info = table_info
        self.enable_binlog = TableConfig.enable_binlog and table_info.enable_binlog

    def _new_profile_log(self):
        log = ProfileLog()
        log.ctime = xutils.format_datetime()
        log.table_name = self.tablename
        log.type = "db_profile"
        return log

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
        start_time = time.time()
        try:
            new_id = self.db.insert(self.tablename, seqname, _test, **values)
            self.add_insert_binlog(new_id, _test=_test)
            return new_id
        except Exception as e:
            del self.db.ctx.db # 尝试重新连接
            raise e
        finally:
            cost_time = time.time() - start_time
            if self.log_profile and self.table_info.log_profile:
                profile_log = self._new_profile_log()
                profile_log.cost_time = cost_time
                profile_log.op_type = "insert"
                self.profile_logger.log(profile_log)
        
    def select(self, vars=None, what='*', where=None, order=None, group=None,
               limit=None, offset=None, _test=False):
        self.fix_sql_keywords(where)
        result_set = self.db.select(self.tablename, vars=vars, what=what, where=where, order=order, group=group,
                              limit=limit, offset=offset, _test=_test)
        records = list(result_set)
        return records
    
    def select_first(self, *args, **kw):
        records = self.select(*args, **kw)
        if len(records) > 0:
            return records[0]
        return None

    def query(self, *args, **kw):
        return list(self.db.query(*args, **kw))

    def count(self, where=None, sql=None, vars=None):
        self.fix_sql_keywords(where)
        if sql is None:
            return self.select_first(what="COUNT(1) AS amount", where=where, vars=vars).amount
        return self.db.query(sql, vars=vars).first().amount

    def update(self, where, vars=None, _test=False, **values):
        self.fix_sql_keywords(where)
        
        start_time = time.time()
        try:
            result = self.db.update(self.tablename, where, vars=vars, _test=_test, **values)
            self.add_update_binlog(where=where, vars=vars, _test=_test)
            return result
        except Exception as e:
            del self.db.ctx.db # 尝试重新连接
            raise e
        finally:
            cost_time = time.time() - start_time
            if self.log_profile and self.table_info.log_profile:
                profile_log = self._new_profile_log()
                profile_log.cost_time = cost_time
                profile_log.op_type = "update"
                self.profile_logger.log(profile_log)

    def delete(self,  where, using=None, vars=None, _test=False):
        if _test:
            # delete为了记录binlog会转换成按照主键删除的sql, 所以这里单独处理下_test场景
            return self.db.delete(self.tablename, where, using=using, vars=vars, _test=True)
        
        self.fix_sql_keywords(where)

        start_time = time.time()
        pk_name = self.table_info.pk_name
        pk_list = []
        
        try:
            for row in self.select(what=pk_name, where=where, vars=vars, _test=_test):
                pk_value = row.get(pk_name)
                pk_list.append(pk_value)
            
            if len(pk_list) > 0:
                new_where = f"`{pk_name}` in $pk_list"
                new_vars = dict(pk_list=pk_list)
                result = self.db.delete(self.tablename, where=new_where, using=using, vars=new_vars, _test=_test)
                self.add_delete_binlog(pk_list)
                return result
        except Exception as e:
            del self.db.ctx.db # 尝试重新连接
            raise e
        finally:
            cost_time = time.time() - start_time
            if self.log_profile and self.table_info.log_profile:
                profile_log = self._new_profile_log()
                profile_log.cost_time = cost_time
                profile_log.op_type = "delete"
                self.profile_logger.log(profile_log)
    
    def transaction(self):
        return self.db.transaction()
    
    def iter(self):
        for records in self.iter_batch():
            for record in records:
                yield record


    def iter_batch(self, batch_size=20, where="", vars=None):
        assert isinstance(where, str)
        
        last_id = 0
        while True:
            this_vars = dict(last_id = last_id)
            if vars != None:
                this_vars.update(vars)
            records = self.select(where = "id > $last_id " + where, vars = this_vars, limit = batch_size, order="id")
            if len(records) == 0:
                break
            yield records
            last_id = records[-1].id
    
    def get_table_info(self):
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

    def add_row_binlog(self, row):
        if not self.enable_binlog:
            return
        if row == None:
            return
        pk_name = self.table_info.pk_name
        pk_value = row.get(pk_name)

        BinLog.get_instance().add_log(BinLogOpType.sql_upsert, pk_value, table_name=self.tablename)

    def add_insert_binlog(self, new_id, _test=False):
        if _test:
            return
        if not self.enable_binlog:
            return
        pk_name = self.table_info.pk_name
        where = {
            pk_name: new_id
        }
        row = self.select_first(where=where)
        self.add_row_binlog(row)

    def add_update_binlog(self, where=None, vars=None, _test=False):
        if _test:
            return
        if not self.enable_binlog:
            return
                
        for row in self.select(where=where, vars=vars):
            self.add_row_binlog(row)

    def add_delete_binlog(self, pk_list=[]):
        if not self.enable_binlog:
            return
        for pk_value in pk_list:
            BinLog.get_instance().add_log(BinLogOpType.sql_delete, pk_value, table_name=self.tablename)
        
