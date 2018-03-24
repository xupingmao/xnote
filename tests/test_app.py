# encoding=utf-8
# Created by xupingmao on 2017/05/23
# @modified 2018/03/16 22:20:19

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
    xconfig.IS_TEST = True
    xconfig.port = "1234"
    xconfig.DEV_MODE = True
    var_env = dict()
    xtables.init()
    app = web.application(list(), var_env, autoreload=False)
    last_mapping = (r"/tools/(.*)", "handlers.tools.tools.handler")
    mgr = xmanager.init(app, var_env, last_mapping=last_mapping)
    mgr.reload()
    return app

app = init()

def json_request(*args, **kw):
    global app
    if "data" in kw:
        # 对于POST请求设置无效
        kw["data"]["_format"] = "json"
    else:
        kw["data"] = dict(_format="json")
    kw["_format"] = "json"
    ret = app.request(*args, **kw)
    if ret.status == "303 See Other":
        return
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
        value = app.request("/file/recent_edit?_format=json").data
        json_value = value.decode("utf-8")
        files = json.loads(json_value)["files"]
        print("files=%s" % len(files))

    def test_fs_func(self):
        if not xutils.is_windows():
            item0, item1 = xutils.splitpath("/fs/test/")
            self.assertEqual("/fs/", item0.path)
            self.assertEqual("/fs/test/", item1.path)

        if xutils.is_windows():
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
        self.check_200("/static/lib/jquery/jquery-1.12.4.min.js")
        # 禁止直接访问目录
        self.check_404("/static/")

    def test_note_add_remove(self):
        self.check_200("/file/recent_edit")
        json_request("/note/remove?name=xnote-unit-test")
        file = json_request("/note/add", method="POST", 
            data=dict(name="xnote-unit-test", content="hello"))
        id = file["id"]
        self.check_OK("/note/view?id=" + str(id))
        json_request("/note/save", method="POST",
            data=dict(id=id, content="new-content"))
        json_request("/note/remove?id=" + str(id))

    def test_file_editor_md(self):
        json_request("/file/remove?name=xnote-md-test")
        file = json_request("/file/add", method="POST",
            data=dict(name="xnote-md-test", type="md", content="hello markdown"))
        id = file["id"]
        file = json_request("/file/view?id=%s&_format=json" % id).get("file")
        self.assertEqual("md", file["type"])
        self.assertEqual("hello markdown", file["content"])
        self.check_200("/file/edit?id=%s"%id)
        json_request("/file/remove?id=%s" % id)

    def test_file_editor_html(self):
        json_request("/file/remove?name=xnote-html-test")
        file = json_request("/file/add", method="POST",
            data=dict(name="xnote-html-test", type="html"))
        id = file["id"]
        self.assertTrue(id != "")
        print("id=%s" % id)
        json_request("/file/save", method="POST", data=dict(id=id, type="html", data="<p>hello</p>"))
        file = json_request("/file/view?id=%s&_format=json" % id).get("file")
        self.assertEqual("html", file["type"])
        self.assertEqual("<p>hello</p>", file["data"])
        if xutils.bs4 != None:
            self.assertEqual("hello", file["content"])
        self.check_200("/file/edit?id=%s"%id)
        json_request("/file/remove?id=%s" % id)

    def test_file_group(self):
        self.check_200("/file/group")
        self.check_200("/file/group/ungrouped")
        self.check_200("/file/group/bookmark")
        self.check_200("/file/recent_edit")

    def test_file_share(self):
        json_request("/file/remove?name=xnote-share-test")
        file = json_request("/file/add", method="POST", 
            data=dict(name="xnote-share-test", content="hello"))
        id = file["id"]
        self.check_OK("/file/share?id=" + str(id))
        file = json_request("/file/view?id=%s&_format=json" % id).get("file")
        self.assertEqual(1, file["is_public"])
        
        self.check_OK("/file/share/cancel?id=" + str(id))
        file = json_request("/file/view?id=%s&_format=json" % id).get("file")
        self.assertEqual(0, file["is_public"])

        json_request("/file/remove?id=" + str(id))

    def test_file_timeline(self):
        json_request("/file/timeline")
        json_request("/file/timeline/month?year=2018&month=1")

    def test_file_dict(self):
        json_request("/file/dict?_format=json")

    def test_fs(self):
        self.check_200("/fs//")
        self.check_200("/fs//?_format=json")
        self.check_200("/data/data.db")

    def test_fs_partial_content(self):
        response = app.request("/data/data.db", headers=dict(RANGE="bytes=1-100"))
        self.assertEqual("206 Partial Content", response.status)
        self.assertEqual("bytes", response.headers["Accept-Ranges"])
        self.assertEqual(True, "Content-Range" in response.headers)

    def test_fs_find(self):
        json_request("/fs_find", method="POST", data=dict(path="./data", find_key="java"))

    def test_code_analyze(self):
        # TODO 解决JSON的循环问题
        self.check_200("/code/analyze?path=./handlers/&key=test")
        self.check_200("/code/analyze?path=./handlers/&key=test&filename=test")

    def test_code_lines(self):
        self.check_OK("/code/lines?count=on&path=./handlers")

    def test_sys(self):
        self.check_200("/system/sys")
        self.check_200("/system/user/list")
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

    def test_script_list(self):
        self.check_200("/system/script_admin")

    def test_script_add_remove(self):
        json_request("/system/script/save", method="POST", data=dict(name="xnote-unit-test.py", content="print(123)"))
        out = xutils.exec_script("xnote-unit-test.py", False, False)
        json_request("/system/script/delete?name=xnote-unit-test.py", method="POST")

    def test_report_time(self):
        self.check_200("/api/report_time")

    def test_tts(self):
        self.check_200("/api/tts?content=测试")

    def test_alarm(self):
        self.check_200("/api/alarm/test?repeat=1")

    def test_search(self):
        self.check_200("/search?key=测试")
        self.check_200("/search/search?key=测试")
    
    def test_search_calc(self):
        result = json_request("/search?key=1%2B2&_format=json")
        value = result['files'][0]['raw']
        self.assertEqual("3", value)

    def test_search_message(self):
        self.check_200("/search?key=test&category=message")

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
        json_request("/file/message/list?status=created")

    def test_tag(self):
        json_request("/file/tag/update", method="POST", data=dict(file_id=0, tags="ABC DEF"))
        json_request("/file/tag/0")
        json_request("/file/tag/update", method="POST", data=dict(file_id=0, tags=""))

    def test_tagname(self):
        self.check_OK("/file/tagname/test")

    def test_document(self):
        self.check_200("/system/document?name=os")
        self.check_200("/system/document?name=xutils")

    def test_view_source(self):
        self.check_200("/code/view_source?path=./README.md")

    def test_view_source_update(self):
        json_request("/code/view_source/update", method="POST", data=dict(path="./test.md", content="hello"))
        content = xutils.readfile("./test.md")
        self.assertEqual("hello", content)
        xutils.remove("./test.md", hard = True)
        
    def test_markdown_preview(self):
        self.check_200("/code/preview?path=./README.md")

    def test_cron_list(self):
        self.check_200("/system/crontab")

    def test_cron_task(self):
        self.check_OK("/system/crontab/add", method="POST", data=dict(url="test", tm_wday="*", tm_hour="*", tm_min="*"))
        sched = xtables.get_schedule_table().select_one(where=dict(url="test"))
        self.check_OK("/system/crontab/remove?id={}".format(sched.id))

        self.check_OK("/system/crontab/add", method="POST", data=dict(script_url="script://test.py", tm_wday="1", tm_hour="*", tm_min="*"))
        sched2 = xtables.get_schedule_table().select_one(where=dict(url="script://test.py"))
        self.check_OK("/system/crontab/remove?id={}".format(sched2.id))

    
    def test_notice_list(self):
        xconfig.clear_notice_list()
        xconfig.add_notice(message="Everyone can see it")
        notice_list = xconfig.get_notice_list(user='admin')
        self.assertEqual(1, len(notice_list))
    
    def test_notice_list_user(self):
        xconfig.clear_notice_list()
        xconfig.add_notice(user="nobody", message="Nobody can see it")
        notice_list = xconfig.get_notice_list(user='admin')
        self.assertEqual(0, len(notice_list))


