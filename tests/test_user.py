# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/01/25 12:48:47
# @modified 2021/09/19 22:49:36

import sys
import time
import unittest
from xnote.core import xauth

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

    def test_change_password(self):
        self.check_OK("/user/change_password")

    def test_user_oplog(self):
        self.check_OK("/user/op_log")

    def test_user_session(self):
        self.check_OK("/user/session")

    def test_refresh_session(self):
        session_info = xauth.login_user_by_name("admin", "127.0.0.1")
        new_session = xauth.refresh_user_session(session_info=session_info)
        assert new_session.sid != session_info.sid

        # test cache hit
        new_session = xauth.refresh_user_session(session_info=session_info)
        assert new_session.sid == session_info.sid