# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-04-28 21:04:36
@LastEditors  : xupingmao
@LastEditTime : 2024-02-15 21:36:55
@FilePath     : /xnote/tests/test_xutils_sqldb.py
@Description  : 描述
"""

from . import test_base
from xutils.sqldb import TableManagerFacade, TableProxy
from xutils.db.binlog import BinLog
from xutils.sqldb import TableConfig
from xnote.core import xconfig
import os
from xnote.core import xtables
import web.db
from xutils.sqldb import utils as sql_utils

app = test_base.init()

class TestMain(test_base.BaseTestCase):

    def clear_table(self, table: TableProxy):
        table.delete(where = "1=1")

    def get_db(self):
        dbpath = os.path.join(xconfig.DB_DIR, "test.db")
        return xtables.get_db_instance(dbpath)
    
    def define_db(self):
        db = self.get_db()
        with TableManagerFacade("unit_test", db = db, check_table_define=False) as table:
            table.add_column("name", "text", default_value="")
            table.add_column("age", "int", default_value=0)
            table.table_info.enable_binlog = True

    def test_db_example(self):
        db = self.get_db()
        self.define_db()

        table = TableProxy(db, "unit_test")
        self.clear_table(table)
        
        table.insert(name = "test-1", age = 10)
        table.insert(name = "test-2", age = 30)

        age10 = table.select_first(where = dict(age=10))
        self.assertEqual("test-1", age10.name)

        first = table.select_first(where = "age=$age", vars=dict(age=10))
        self.assertEqual("test-1", first.name)

        count = table.count(where="age=$age", vars=dict(age=10))
        self.assertEqual(1, count)


    def test_db_binlog(self):
        db = self.get_db()
        self.define_db()
        TableConfig.enable_binlog = True
        web.db.config.debug_sql = True

        table = TableProxy(db, "unit_test")
        self.clear_table(table)

        BinLog.get_instance().set_enabled(True)
        new_id = table.insert(name="test-1", age=10)
        last_log = BinLog.get_instance().get_last_log()

        assert isinstance(last_log, dict)
        assert last_log.get("key") == new_id
        assert last_log.get("table_name") == table.tablename
        assert last_log.get("optype") == "sql_upsert"

        table.update(where=dict(name="test-1"), age=20)
        last_log = BinLog.get_instance().get_last_log()
        assert isinstance(last_log, dict)
        assert last_log.get("key") == new_id
        assert last_log.get("table_name") == table.tablename
        assert last_log.get("optype") == "sql_upsert"

        table.delete(where=dict(name="test-1"))
        last_log = BinLog.get_instance().get_last_log()
        assert isinstance(last_log, dict)
        assert last_log.get("key") == new_id
        assert last_log.get("table_name") == table.tablename
        assert last_log.get("optype") == "sql_delete"

    def test_safe_str(self):
        s = sql_utils.safe_str(None)
        assert s == ""
        s = sql_utils.safe_str("1234", max_length=2)
        assert s == "12"
        s = sql_utils.safe_str("1234")
        assert s == "1234"

