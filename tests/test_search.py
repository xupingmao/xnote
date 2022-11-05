# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/07/18 18:36:23
# @modified 2021/07/18 19:45:09
# @filename test_search.py

from . import test_base

app          = test_base.init()
json_request = test_base.json_request
request_html = test_base.request_html
BaseTestCase = test_base.BaseTestCase

class TestMain(BaseTestCase):

    def test_search(self):
        self.check_OK("/search")

    def test_search_message(self):
        self.check_OK("/search?category=message")

    def test_search_calc(self):
        result = json_request("/search?key=1%2B2&_format=json")
        value = result['files'][0]['raw']
        self.assertEqual("1+2=3", value)
    
    def test_search_note(self):
        self.check_OK("/search?search_type=note&key=test")
    
    def test_search_dict(self):
        self.check_OK("/search?search_type=dict&key=test")
    
    def test_search_task(self):
        self.check_OK("/search?search_type=task&key=test")

    def test_search_comment(self):
        self.check_OK("/search?search_type=comment&key=test")

    def test_search_history(self):
        from handlers.note import dao
        dao.add_search_history(None, "test")
        dao.expire_search_history("user")
        dao.list_search_history("user")
