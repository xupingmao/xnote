# encoding=utf-8
from . import base
from xutils import dbutil
from xutils.db.binlog import BinLog

def do_upgrade():
    base.execute_upgrade("20230709", fix_binlog_20230709)

class BatchDelete:

    def __init__(self):
        self.batch = []
        self.batch_size = 100

    def delete(self, key=""):
        self.batch.append(key)
        if len(self.batch) > self.batch_size:
            dbutil.db_batch_delete(self.batch)
            self.batch = []
    
    def commit(self):
        if len(self.batch) > 0:
            dbutil.db_batch_delete(self.batch)

def fix_binlog_20230709():
    """删除老版本的binlog"""
    binlog = BinLog.get_instance()
    batch_delete = BatchDelete()
    for key, value in dbutil.prefix_iter(binlog._table_name, limit=-1, include_key=True):
        table_name, log_id = key.split(":")
        if len(log_id) == 20:
            batch_delete.delete(key)
    batch_delete.commit()

