# encoding=utf-8
import sys
sys.path.insert(1, "lib")
sys.path.insert(1, "core")
import os
import time
import unittest
import xconfig
import xutils
import xtables
import xmanager
import xtemplate
import web
import six
import json
from xutils import get_upload_file_path
from xutils import dbutil

config = xconfig
date = time.strftime("%Y/%m")

APP = None

def init():
    global APP
    if APP is not None:
        return APP
    xconfig.IS_TEST = True
    xconfig.port = "1234"
    xconfig.DEV_MODE = True
    var_env = dict()
    xutils.remove_file("./testdata/data.db", hard = True)
    xconfig.init("./testdata")
    xtables.init()
    dbutil.init()
    APP = web.application(list(), var_env, autoreload=False)
    last_mapping = (r"/tools/(.*)", "handlers.tools.tools.handler")
    mgr = xmanager.init(APP, var_env, last_mapping=last_mapping)
    mgr.reload()
    # 加载template
    xtemplate.reload()
    return APP

def json_request(*args, **kw):
    global APP
    if "data" in kw:
        # 对于POST请求设置无效
        kw["data"]["_format"] = "json"
    else:
        kw["data"] = dict(_format="json")
    kw["_format"] = "json"
    ret = APP.request(*args, **kw)
    if ret.status == "303 See Other":
        return
    assert ret.status == "200 OK"
    data = ret.data
    if six.PY2:
        return json.loads(data)
    return json.loads(data.decode("utf-8"))

def request_html(*args, **kw):
    ret = APP.request(*args, **kw)
    return ret.data

def create_tmp_file(name):
    path = os.path.join(xconfig.DATA_DIR, "files", "user", "upload", time.strftime("%Y/%m"), name)
    xutils.touch(path)

def remove_tmp_file(name):
    path = os.path.join(xconfig.DATA_DIR, "files", "user", "upload", time.strftime("%Y/%m"), name)
    if os.path.exists(path):
        os.remove(path)

class BaseTestCase(unittest.TestCase):

    def check_OK(self, *args, **kw):
        response = APP.request(*args, **kw)
        status = response.status
        print(status)
        self.assertEqual(True, status == "200 OK" or status == "303 See Other" or status == "302 Found")

    def check_200(self, *args, **kw):
        response = APP.request(*args, **kw)
        self.assertEqual("200 OK", response.status)

    def check_303(self, *args, **kw):
        response = APP.request(*args, **kw)
        self.assertEqual("303 See Other", response.status)

    def check_404(self, url):
        response = APP.request(url)
        self.assertEqual("404 Not Found", response.status)

    def check_status(self, status, *args, **kw):
        response = APP.request(*args, **kw)
        self.assertEqual(status, response.status)

    def json_request(self, *args, **kw):
        return json_request(*args, **kw)

class BaseTestMain(unittest.TestCase):

    def test_get_upload_file_path(self):
        remove_tmp_file("test.txt")
        path, webpath = get_upload_file_path("user", "test.txt")
        print()
        print(path)
        print(webpath)
        self.assertEqual(os.path.abspath(config.DATA_PATH + "/files/user/upload/%s/test.txt" % date), path)
        self.assertEqual("/data/files/user/upload/%s/test.txt" % date, webpath)

    def test_get_upload_file_path_1(self):
        remove_tmp_file("test_1.txt")
        create_tmp_file("test.txt")
        path, webpath = get_upload_file_path("user", "test.txt")
        print()
        print(path)
        print(webpath)
        self.assertEqual(os.path.abspath(config.DATA_PATH + "/files/user/upload/%s/test_1.txt" % date), path)
        self.assertEqual("/data/files/user/upload/%s/test_1.txt" % date, webpath)
        remove_tmp_file("test.txt")

    def test_get_upload_file_path_2(self):
        create_tmp_file("test.txt")
        create_tmp_file("test_1.txt")
        remove_tmp_file("test_2.txt")
        path, webpath = get_upload_file_path("user", "test.txt")
        print()
        print(path)
        print(webpath)
        self.assertEqual(os.path.abspath(config.DATA_PATH + "/files/user/upload/%s/test_2.txt" % date), path)
        self.assertEqual("/data/files/user/upload/%s/test_2.txt" % date, webpath)
        remove_tmp_file("test.txt")
        remove_tmp_file("test_1.txt")

