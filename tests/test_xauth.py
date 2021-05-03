# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/01/24 16:39:45
# @modified 2021/05/03 17:55:58

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

class TestXauth(BaseTestCase):

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

