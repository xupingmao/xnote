# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/11/29 14:45:21
# @modified 2021/10/07 15:04:35

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
from xutils import u, dbutil

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

    def test_fs_hex(self):
        self.check_OK("/fs/fs_hex")
        self.check_OK("/fs/fs_hex?path=./README.md")

    def test_fs_tools(self):
        self.check_OK("/fs_tools")
        self.check_OK("/fs_bookmark")
