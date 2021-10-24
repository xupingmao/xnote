# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/01/24 16:39:45
# @modified 2021/10/24 16:47:44

import sys
import time
import unittest
sys.path.insert(1, "lib")
sys.path.insert(1, "core")
import xauth
from xutils import Storage
from xutils import dateutil

# cannot perform relative import
try:
    import test_base
except ImportError:
    from tests import test_base

BaseTestCase = test_base.BaseTestCase

app = test_base.init()

class TestXauth(BaseTestCase):

    def test_current_user(self):
        self.assertEqual("test", xauth.current_name())

    def test_check_invalid_names(self):
        self.assertTrue(xauth.is_valid_username("t1234"))
        self.assertFalse(xauth.is_valid_username("public"))

    def test_create_and_delete_user(self):
        # 创建用户
        result = xauth.create_user("u123456", "123456")
        print(result)

        users = xauth.refresh_users()
        print(users)
        self.assertEqual(3, len(users))

        # 删除用户
        xauth.delete_user("u123456")

        check = xauth.find_by_name("u123456")
        self.assertEqual(None, check)

    def test_list_user_names(self):
        user_names = xauth.list_user_names()
        self.assertTrue(len(user_names) >= 1)

    def test_login_logout(self):
        self.check_OK("/")
        # TODO 待修复
        # AttributeError: 'ThreadedDict' object has no attribute 'homepath'
        # xauth.login_user_by_name("test")
        # xauth.logout_current_user()

    def test_create_and_list_user_session(self):
        # 先清理
        for sid in xauth.list_user_session_id("admin"):
            xauth.delete_user_session_by_id(sid)

        # 创建并且查询
        xauth.create_user_session("admin")
        result = xauth.list_user_session_detail("admin")
        self.assertTrue(len(result) == 1)

    def test_update_user(self):
        result = xauth.create_user("u123456", "123456")
        print(result)

        datetime = dateutil.format_time()
        user_info = Storage(login_time = datetime)
        xauth.update_user("u123456", user_info)

        self.assertTrue(datetime, xauth.get_user_by_name("u123456").login_time)

        xauth.delete_user("u123456")



