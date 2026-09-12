# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/07/18 18:36:23
# @modified 2021/07/18 19:45:09
# @filename test_search.py

from . import test_base
from .test_base import json_request_return_dict
from xnote.core import xauth
from xnote.core import xtables
from xnote_handlers.plugin.dao import add_visit_log, delete_visit_log
from xnote.plugin import db as plugin_db

app          = test_base.init()
json_request = test_base.json_request
request_html = test_base.request_html
BaseTestCase = test_base.BaseTestCase

class TestMain(BaseTestCase):

    def test_plugin_list(self):
        self.check_OK("/plugin_list")

    def test_table(self):
        self.check_OK("/test/example/table?name=table")

    def test_contribution_calendar(self):
        self.check_OK("/test/example/calendar?name=calendar")

    def test_list(self):
        self.check_OK("/test/example/list?name=list")

    def test_list_plugin(self):
        self.check_OK("/test/example/list_plugin")

    def test_tag_example(self):
        # Tag 示例页展示新增的浅红/浅紫标签
        body = self.request_app("/test/example?name=tag").data.decode("utf-8")
        self.assertIn("lightred标签", body)
        self.assertIn("lightpurple标签", body)

    def test_plugin_visit(self):
        delete_visit_log(user_name="admin", url="/test")
        assert add_visit_log(user_name="admin", url="/test") == 1
        assert add_visit_log(user_name="admin", url="/test") == 2

    def test_plugin_manage(self):
        self.check_OK("/plugin_manage")
        
    def test_plugin_db(self):
        with plugin_db.create_plugin_table(table_name="plugin_test") as manager:
            manager.add_column("name", "text", default_value="", comment="name")
            manager.add_column("age", "int", default_value=0)
        
        db = xtables.get_table_by_name("plugin_test")
        db.insert(name = "test", age = 20)
        results = db.select()
        print(f"results={results}")
        assert len(results) > 0

