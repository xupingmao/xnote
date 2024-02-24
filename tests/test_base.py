# encoding=utf-8
from .a import *
import os
import time
import unittest
from xnote.core import xconfig
import xutils
from xnote.core import xtables
from xnote.core import xmanager
from xnote.core import xtemplate
from xnote.core import xtables_kv
import web
import json
from xnote.core import xauth
from xutils import dbutil
from xutils import cacheutil
from xutils import six
from xutils.db.driver_sqlite import SqliteKV

config = xconfig
date = time.strftime("%Y/%m")

APP: web.application = None

DEFAULT_HEADERS = dict()


def init():
    global APP
    if APP is not None:
        return APP
    xconfig.init("./config/boot/boot.test.properties")
    xconfig.IS_TEST = True
    
    xauth.TestEnv.login_admin()
    
    xconfig.port = "1234"
    xconfig.DEV_MODE = True
    var_env = dict()
    xutils.remove_file("./testdata/data.db", hard=True)
    xtables.init()

    db_file = os.path.join(xconfig.DB_DIR, "sqlite", "test.db")
    db_instance = SqliteKV(db_file)
    dbutil.init(xconfig.DB_DIR, db_instance=db_instance, binlog_max_size=1000)
    xtables_kv.init()

    xutils.init(xconfig)
    xauth.init()
    cacheutil.init(xconfig.STORAGE_DIR)

    APP = web.application(list(), var_env, autoreload=False)
    last_mapping = (r"/tools/(.*)", "handlers.tools.tools.handler")
    mgr = xmanager.init(APP, var_env, last_mapping=last_mapping)
    mgr.reload()
    # 加载template
    xtemplate.reload()

    xauth.create_user("test2", "123456")

    # 发送启动消息
    xmanager.fire("sys.reload")

    return APP


APP = init()


def get_test_file_path(path):
    return os.path.join("./testdata", path)


def logout_test_user():
    xauth.TestEnv.logout()


def login_test_user(user_name="admin"):
    xauth.TestEnv.login_user(user_name)


def json_request(*args, **kw):
    global APP
    if "data" in kw:
        # 对于POST请求设置无效
        kw["data"]["_format"] = "json"
    else:
        kw["data"] = dict(_format="json")
    kw["_format"] = "json"
    kw["headers"] = DEFAULT_HEADERS

    ret = APP.request(*args, **kw)
    if ret.status == "303 See Other":
        return
    assert ret.status == "200 OK"
    data = ret.data
    if six.PY2:
        return json.loads(data)
    return json.loads(data.decode("utf-8"))

def json_request_return_dict(*args, **kw):
    """请求接口,返回json,实例如下
    - json_request_return_dict("/api/test", method="POST", data=dict(name="test"))
    - json_request_return_dict("/api/get_info?p1=1&p2=test")
    """
    ret = json_request(*args, **kw)
    assert isinstance(ret, dict)
    return ret

def request_html(*args, **kw):
    ret = APP.request(*args, **kw)
    return ret.data


def create_tmp_file(name):
    path = os.path.join(xconfig.DATA_DIR, "files", "user",
                        "upload", time.strftime("%Y/%m"), name)
    xutils.touch(path)


def remove_tmp_file(name):
    path = os.path.join(xconfig.DATA_DIR, "files", "user",
                        "upload", time.strftime("%Y/%m"), name)
    if os.path.exists(path):
        os.remove(path)


class BaseTestCase(unittest.TestCase):

    def request_app(self, *args, **kw):
        return APP.request(*args, **kw)

    def check_OK(self, *args, **kw):
        response = APP.request(*args, **kw)
        status = response.status
        print("response.status:", status)
        self.assertIn(status, ("200 OK", "303 See Other", "302 Found"))

    def check_200(self, *args, **kw):
        response = APP.request(*args, **kw)
        self.assertEqual("200 OK", response.status)

    def check_200_debug(self, *args, **kw):
        response = APP.request(*args, **kw)
        print(args, kw, response)
        print(APP.mapping)
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

    def json_request_return_dict(self, *args, **kw):
        return json_request_return_dict(*args, **kw)

class BaseTestMain(unittest.TestCase):

    def test_get_upload_file_path(self):
        from handlers.fs.fs_upload import get_upload_file_path
        remove_tmp_file("test.txt")
        path, webpath = get_upload_file_path("user", "test.txt")
        print()
        print(path)
        print(webpath)
        self.assertEqual(os.path.abspath(config.DATA_PATH +
                         "/files/user/upload/%s/test.txt" % date), path)
        self.assertEqual("/data/files/user/upload/%s/test.txt" % date, webpath)

    def test_get_upload_file_path_1(self):
        from handlers.fs.fs_upload import get_upload_file_path
        remove_tmp_file("test_1.txt")
        create_tmp_file("test.txt")
        path, webpath = get_upload_file_path("user", "test.txt")
        print()
        print(path)
        print(webpath)
        self.assertEqual(os.path.abspath(config.DATA_PATH +
                         "/files/user/upload/%s/test_1.txt" % date), path)
        self.assertEqual(
            "/data/files/user/upload/%s/test_1.txt" % date, webpath)
        remove_tmp_file("test.txt")

    def test_get_upload_file_path_2(self):
        from handlers.fs.fs_upload import get_upload_file_path
        create_tmp_file("test.txt")
        create_tmp_file("test_1.txt")
        remove_tmp_file("test_2.txt")
        path, webpath = get_upload_file_path("user", "test.txt")
        print()
        print(path)
        print(webpath)
        self.assertEqual(os.path.abspath(config.DATA_PATH +
                         "/files/user/upload/%s/test_2.txt" % date), path)
        self.assertEqual(
            "/data/files/user/upload/%s/test_2.txt" % date, webpath)
        remove_tmp_file("test.txt")
        remove_tmp_file("test_1.txt")


class ResponseWrapper:

    def __init__(self, resp: web.Storage) -> None:
        self.resp = resp

    def get_header(self, header: str):
        header = header.lower()
        headers = self.resp.header_items
        for key, value in headers:
            if key.lower() == header:
                return value
        return None
