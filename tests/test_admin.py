# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-10-14 09:30:29
@LastEditors  : xupingmao
@LastEditTime : 2024-01-01 17:38:55
@FilePath     : /xnote/tests/test_admin.py
@Description  : 描述
"""

from . import test_base
from xnote.core import xconfig, xmanager, xauth
import web.utils

app = test_base.init()

class TestMain(test_base.BaseTestCase):
    """测试管理后台的功能"""
    
    def test_db_struct(self):
        self.check_OK("/system/db/struct?table_name=user")
        
        
    def assert_no_auth(self, response):
        if response.status == "401 Unauthorized":
            return
        
        if "/unauthorized" in response.headers['Location']:
            return
        raise Exception("发现权限拦截漏洞")

    def test_admin_auth(self):
        print("")
        
        skip_list = set([
            "/system/settings",
            "/system/stats",
            "/system/stats/location",
            "/system/index",
            "/system/sys",
            "/system/system",
            r"/system/user\.css",
            r"/system/user\.js",
            "/system/log/visit",
            "/system/todo",
        ])

        check_list = set([
            "/plugins_upload",
            "/plugins_new",
            "/plugins_new/command",
        ])

        try:
            # 登录普通用户
            xauth.TestEnv.login_user("test")

            mapping = xmanager.get_handler_manager().mapping
            
            for pattern, raw_handler in web.utils.group(mapping, 2):
                if pattern in skip_list:
                    continue
                if pattern.startswith("/system/") or pattern in check_list:
                    print(f"Check {pattern} ...")
                    handler = raw_handler.handler_class
                    check_pass = False
                    if hasattr(handler, "GET"):
                        response = self.request_app(pattern, method="GET")
                        self.assert_no_auth(response)
                        check_pass = True
                    
                    if hasattr(handler, "POST"):
                        response = self.request_app(pattern, method="POST")
                        self.assert_no_auth(response)
                        check_pass = True
                    assert check_pass
        finally:
            xauth.TestEnv.login_user("admin")
        
    