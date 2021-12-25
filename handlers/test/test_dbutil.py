# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/18 17:37:52
# @modified 2021/12/18 23:30:28
# @filename test_dbutil.py

import xauth
import xutils
import random
from xutils import Storage
from xutils import dbutil

dbutil.register_table("test", "测试数据库")
dbutil.register_table("_index:test", "测试数据库索引")

def get_test_db():
    db = dbutil.get_table("test")
    db.define_index("age")
    return db

def get_test_index_db():
    return dbutil.get_hash_table("_index:test")

class TestHandler:

    @xauth.login_required("admin")
    def GET(self):
        p = xutils.get_argument("p", "")
        if p == "clear":
            return self.clear_data()

        db = get_test_db()

        for i in range(1,11):
            id_value = "name_%s" % i
            row = Storage(name = id_value, age = random.randint(0, 10))
            db.insert(row, id_type = None, id_value = id_value)

        result = Storage()
        result.list = db.list()
        result.list_by_age = db.list_by_index("age")

        return xutils.tojson(result, format=True)

    def clear_data(self):
        db = get_test_db()
        count = 0
        for item in db.iter(limit = -1):
            db.delete(item)
            count += 1

        index_count = self.clear_index_data()
        return dict(count = count, index_count = index_count)

    def clear_index_data(self):
        db = get_test_index_db()
        count = 0
        for key, value in db.iter(limit = -1):
            db.delete(key)
            count += 1
        return count


xurls = (
    r"/test/test_dbutil", TestHandler
)