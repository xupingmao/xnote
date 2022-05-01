# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-01 12:52:24
@LastEditors  : xupingmao
@LastEditTime : 2022-05-01 15:09:21
@FilePath     : /xnote/tests/test_dict.py
"""

from .test_base import json_request, BaseTestCase
from .test_base import init as init_app

app = init_app()

class TestMain(BaseTestCase):

    def test_dict(self):
        json_request("/dict/edit/name", method = "POST", data = dict(name = "name", value = u"姓名".encode("utf-8")))
        self.check_OK("/note/dict")
        self.check_OK("/dict/search?key=name")
    
    def test_dict_relevant(self):
        self.check_OK("/dict/relevant/list")
        resp1 = json_request("/dict/relevant/add_words", method = "POST", data = dict(words = "test1 test2"))
        self.assertEqual("success", resp1["code"])

        resp2 = json_request("/dict/relevant/list?_format=json", method = "GET")
        self.assertEqual(2, len(resp2["words"]))

        resp2b = json_request("/dict/relevant/list?_format=json&key=test1")
        self.assertEqual(1, len(resp2b["words"]))

        resp3 = json_request("/dict/relevant/delete", method = "POST", data = dict(word = "test1"))
        self.assertEqual("success", resp3["code"])

        resp4 = json_request("/dict/relevant/list?_format=json", method = "GET")
        self.assertEqual(0, len(resp4["words"]))