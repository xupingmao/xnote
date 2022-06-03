# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/11/29 14:45:21
# @modified 2022/06/03 14:33:36
from .a import *
import os
import xconfig
import xauth
from .test_base import json_request, BaseTestCase
from .test_base import init as init_app
from handlers.fs.fs_index import build_fs_index

app = init_app()


class TestMain(BaseTestCase):

    def test_fs_view_mode(self):
        cwd = os.getcwd()

        self.check_OK("/fs/{cwd}".format(cwd=cwd))
        self.check_OK("/fs/{cwd}?mode=grid".format(cwd=cwd))

    def test_fs_hex(self):
        self.check_OK("/fs/fs_hex")
        self.check_OK("/fs/fs_hex?path=./README.md")

    def test_fs_tools(self):
        self.check_OK("/fs_tools")
        self.check_OK("/fs_bookmark")

    def test_create_file(self):
        path = xconfig.DATA_DIR
        resp = json_request("/fs_api/add_file", method="POST",
                            data=dict(path=path, filename="test_fs.txt"))
        print(resp)
        self.assertEqual("success", resp["code"])

    def test_create_dir(self):
        path = xconfig.DATA_DIR
        resp = json_request("/fs_api/add_dir", method="POST",
                            data=dict(path=path, filename="test_fs_dir"))
        print(resp)
        self.assertEqual("success", resp["code"])
    
    def test_code_preview(self):
        self.check_OK("/code/preview?path=./README.md")

    def test_build_fs_index(self):
        size = build_fs_index(xconfig.DATA_DIR)
        self.assertTrue(size > 0)

    def test_config_fs_order(self):
        resp = json_request("/fs_api/config", method = "POST", data = dict(action = "sort", order = "size"))
        print(resp)
        self.assertEqual("success", resp["code"])
        
        user_name = xauth.current_name()
        self.assertEqual("size", xauth.get_user_config(user_name, "fs_order"))
    
    def test_fs_config_error(self):
        resp = json_request("/fs_api/config", method = "POST", data = dict(action = "notfount", order = "size"))
        print(resp)
        self.assertEqual("error", resp["code"])
