# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/01/25 12:48:47
# @modified 2021/09/19 22:49:36

import sys
import time
import unittest
from xnote.core import xauth
from xnote.core.xnote_user_config import UserConfig
from xnote.core.test_env import TestEnv
# cannot perform relative import
try:
    import test_base
except ImportError:
    from tests import test_base

json_request_return_dict = test_base.json_request_return_dict


BaseTestCase = test_base.BaseTestCase

app = test_base.init()

TestEnv.is_test = True

class TestUser(BaseTestCase):

    def test_login_page(self):
        self.check_OK("/login")

    def test_change_password(self):
        self.check_OK("/user/change_password")

    def test_user_oplog(self):
        self.check_OK("/user/op_log")

    def test_user_session(self):
        self.check_OK("/user/session")

    def test_user_info(self):
        self.check_OK("/user/info")

    def test_refresh_session(self):
        session_info = xauth.login_user_by_name("admin", "127.0.0.1")
        new_session = xauth.refresh_user_session(session_info=session_info)
        assert new_session.sid != session_info.sid

        # test cache hit
        new_session = xauth.refresh_user_session(session_info=session_info)
        assert new_session.sid == session_info.sid

    def test_user_config(self):
        config_key = UserConfig.task_filter.key
        self.check_OK(f"/code/edit/user_config?config_key={config_key}")

        data = {}
        data["config_key"] = config_key
        data["content"] = "test #tag1# #tag2#"
        json_request_return_dict("/code/edit/user_config", method="POST", data=data)

    def test_user_switch_account(self):
        self.check_OK("/user/switch_account")
        self.check_OK("/user/switch_account?event_type=click&selected_sid=1234")