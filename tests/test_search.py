# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/07/18 18:36:23
# @modified 2021/07/18 19:45:09
# @filename test_search.py

import sys
import os
sys.path.insert(1, "lib")
sys.path.insert(1, "core")
import unittest
import json
import web
import six
import xmanager
import xutils
import xtemplate
import xconfig
import xtables
from xutils import u
from xutils import dbutil
from xutils import dateutil

# cannot perform relative import
try:
    import test_base
except ImportError:
    from tests import test_base

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