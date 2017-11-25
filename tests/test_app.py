# encoding=utf-8
# Created by xupingmao on 2017/05/23

import sys
sys.path.insert(1, "lib")

import unittest
import json
import web
import six

import xmanager
import xutils
import xtemplate
import xconfig
import xtables

from xutils import u

def init():
    xtables.init()
    xconfig.IS_TEST = True
    xconfig.port = "1234"
    var_env = dict()
    app = web.application(list(), var_env, autoreload=False)
    last_mapping = (r"/tools/(.*)", "handlers.tools.tools.handler")
    mgr = xmanager.init(app, var_env, last_mapping=last_mapping)
    mgr.reload()
    return app

app = init()

def json_request(*args, **kw):
    global app
    if "data" in kw:
        kw["data"]["_type"] = "json"
    kw["_type"] = "json"
    ret = app.request(*args, **kw)
    data = ret.data
    if six.PY2:
        return json.loads(data)
    return json.loads(data.decode("utf-8"))

class TestMain(unittest.TestCase):

    def test_xtables(self):
        xtables.init_table_test()

    def test_render_text(self):
        value = xtemplate.render_text("Hello,{{name}}", name="World")
        self.assertEqual(b"Hello,World", value)

    def test_render(self):
        value = app.request("/test").data
        self.assertEqual(b"success", value)

    def test_recent_files(self):
        value = app.request("/file/recent_edit?_type=json").data
        json_value = value.decode("utf-8")
        files = json.loads(json_value)["files"]
        print("files=%s" % len(files))

    def test_fs_func(self):
        item0, item1 = xutils.splitpath("/fs/test/")
        self.assertEqual("/fs/", item0.path)
        self.assertEqual("/fs/test/", item1.path)

        item0, item1, item2 = xutils.splitpath("C:/data/name/")
        self.assertEqual("C:/", item0.path)
        self.assertEqual("C:/data/", item1.path)
        self.assertEqual("C:/data/name/", item2.path)

    def check_OK(self, *args, **kw):
        response = app.request(*args, **kw)
        status = response.status
        self.assertEqual(True, status == "200 OK" or status == "303 See Other")

    def check_200(self, *args, **kw):
        response = app.request(*args, **kw)
        self.assertEqual("200 OK", response.status)

    def check_303(self, *args, **kw):
        response = app.request(*args, **kw)
        self.assertEqual("303 See Other", response.status)

    def check_404(self, url):
        response = app.request(url)
        self.assertEqual("404 Not Found", response.status)

    def check_status(self, status, *args, **kw):
        response = app.request(*args, **kw)
        self.assertEqual(status, response.status)

    def test_static_files(self):
        self.check_200("/static/lib/jquery.js")
        # 禁止直接访问目录
        self.check_404("/static/")

    def test_file(self):
        self.check_200("/file/recent_edit")
        json_request("/file/remove?name=xnote-unit-test")
        file = json_request("/file/add", method="POST", 
            data=dict(name="xnote-unit-test", content="hello"))
        id = file["id"]
        self.check_OK("/file/view?id=" + str(id))
        json_request("/file/remove?id=" + str(id))

    def test_file_editor_md(self):
        json_request("/file/remove?name=xnote-md-test")
        file = json_request("/file/add", method="POST",
            data=dict(name="xnote-md-test", type="md", content="hello markdown"))
        id = file["id"]
        file = json_request("/file/view?id=%s&_type=json" % id).get("file")
        self.assertEqual("md", file["type"])
        self.assertEqual("hello markdown", file["content"])
        json_request("/file/remove?id=%s" % id)

    def test_file_editor_html(self):
        json_request("/file/remove?name=xnote-html-test")
        file = json_request("/file/add", method="POST",
            data=dict(name="xnote-html-test", type="html"))
        id = file["id"]
        json_request("/file/save", method="POST", data=dict(id=id, type="html", data="<p>hello</p>"))
        file = json_request("/file/view?id=%s&_type=json" % id).get("file")
        self.assertEqual("html", file["type"])
        self.assertEqual("<p>hello</p>", file["data"])
        if xutils.bs4 != None:
            self.assertEqual("hello", file["content"])
        json_request("/file/remove?id=%s" % id)

    def test_group(self):
        self.check_200("/file/group")
        self.check_200("/file/group/memo")
        self.check_200("/file/group/ungrouped")
        self.check_200("/file/group/bookmark")
        self.check_200("/file/recent_edit")


    def test_fs(self):
        self.check_200("/fs//")
        self.check_200("/fs//?_type=json")
        self.check_200("/data/data.db")

    def test_fs_partial_content(self):
        response = app.request("/data/data.db", headers=dict(RANGE="bytes=1-100"))
        self.assertEqual("206 Partial Content", response.status)
        self.assertEqual("bytes", response.headers["Accept-Ranges"])
        self.assertEqual(True, "Content-Range" in response.headers)

    def test_sys(self):
        self.check_200("/system/sys")
        self.check_200("/system/user_admin")
        self.check_200("/system/sys_var_admin")
        self.check_200("/system/crontab")
        self.check_200("/system/stats")
        self.check_200("/system/stats/location", method="POST")

    def test_tools(self):
        self.check_200("/tools/sql")
        self.check_200("/tools/color")

    def test_backup_info(self):
        self.check_200("/system/backup_info")

    def test_notfound(self):
        self.check_404("/nosuchfile")

    def test_script_admin(self):
        self.check_200("/system/script_admin")

    def test_report_time(self):
        self.check_200("/api/report_time")

    def test_tts(self):
        self.check_200("/system/tts?content=测试")

    def test_alarm(self):
        self.check_200("/api/alarm/test?repeat=1")

    def test_task(self):
        self.check_200("/system/crontab")
        self.check_OK("/system/crontab/add", method="POST", data=dict(url="test", tm_wday="*", tm_hour="*", tm_min="*"))
        sched = xtables.get_schedule_table().select_one(where=dict(url="test"))
        self.check_OK("/system/crontab/remove?id={}".format(sched.id))

        self.check_OK("/system/crontab/add", method="POST", data=dict(script_url="script://test.py", tm_wday="1", tm_hour="*", tm_min="*"))
        sched2 = xtables.get_schedule_table().select_one(where=dict(url="script://test.py"))
        self.check_OK("/system/crontab/remove?id={}".format(sched2.id))

    def test_search(self):
        self.check_200("/search?key=测试")
        self.check_200("/search/search?key=测试")

    def test_http_headers(self):
        data = app.request("/api/http_headers", headers=dict(X_TEST=True)).data
        self.assertEqual(True, b"HTTP_X_TEST" in data)

    def test_message_add(self):
        # Py2: webpy会自动把str对象转成unicode对象，data参数传unicode反而会有问题
        response = json_request("/file/message/add", method="POST", data=dict(content="Xnote测试"))
        self.assertEqual("success", response.get("code"))
        data = response.get("data")
        # Py2: 判断的时候必须使用unicode
        self.assertEqual(u"Xnote测试", data.get("content"))
        json_request("/file/message/remove", method="POST", data=dict(id=data.get("id")))

    def test_message_list(self):
        json_request("/file/message/list")


