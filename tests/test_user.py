# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/01/25 12:48:47
# @modified 2020/01/25 12:49:41

import sys
import time
import unittest
sys.path.insert(1, "lib")
sys.path.insert(1, "core")
import xauth

# cannot perform relative import
try:
    import test_base
except ImportError:
    from tests import test_base

BaseTestCase = test_base.BaseTestCase

app = test_base.init()

class TestUser(BaseTestCase):

    def test_login_page(self):
        self.check_OK("/login")

