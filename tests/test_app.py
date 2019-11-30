# encoding=utf-8
# Created by xupingmao on 2017/05/23
# @modified 2019/11/30 19:17:45

import sys
import os
sys.path.insert(1, "lib")
sys.path.insert(1, "core")
import unittest
import json
import web
import six
import xmanager
import xutils
import xtemplate
import xconfig
import xtables
from xutils import u, dbutil

# cannot perform relative import
try:
    import test_base
except ImportError:
    from tests import test_base

app          = test_base.init()
json_request = test_base.json_request
request_html = test_base.request_html
BaseTestCase = test_base.BaseTestCase

def get_script_path(name):
    return os.path.join(xconfig.SCRIPTS_DIR, name)

class TextPage(xtemplate.BaseTextPlugin):

    def get_input(self):
        return ""

    def get_format(self):
        return ""

    def handle(self, input):
        return "test"

class TestMain(BaseTestCase):

    def test_xtables(self):
        xtables.init_test_table()

    def test_render_text(self):
        value = xtemplate.render_text("Hello,{{name}}", name="World")
        self.assertEqual(b"Hello,World", value)

    def test_render(self):
        value = app.request("/test").data
        self.assertEqual(b"success", value)

    def test_recent_files(self):
        value = app.request("/note/recent_edit?_format=json").data
        json_value = value.decode("utf-8")
        files = json.loads(json_value)["files"]
        print("files=%s" % len(files))

    def test_index(self):
        self.check_OK("/")
        self.check_OK("/index")

    def test_home(self):
        self.check_OK("/home")

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

    def test_static_files(self):
        self.check_200("/static/lib/jquery/jquery-1.12.4.min.js")
        # 禁止直接访问目录
        self.check_404("/static/")

    def test_dict_json(self):
        json_request("/note/dict?_format=json")

    def test_dict(self):
        self.check_200("/note/dict")

    def test_dict_edit(self):
        self.check_200("/dict/edit/test")

    def test_fs(self):
        self.check_200("/fs//")
        self.check_200("/fs//?_format=json")
        # self.check_200("/data/data.db")

    def test_fs_partial_content(self):
        fpath = os.path.join(xconfig.DATA_DIR, "test.txt")
        xutils.writefile(fpath, "test")
        response = app.request("/data/test.txt", headers=dict(RANGE="bytes=1-100"))
        self.assertEqual("206 Partial Content", response.status)
        self.assertEqual("bytes", response.headers["Accept-Ranges"])
        self.assertEqual(True, "Content-Range" in response.headers)

    def test_fs_find(self):
        json_request("/fs_find", method="POST", data=dict(path="./data", find_key="java"))
        self.check_OK("/fs_index")
        self.check_OK("/fs_index", method="POST", action="reindex")

    def test_fs_plugins(self):
        self.check_OK("/fs_api/plugins?path=/")

    def test_fs_sidebar(self):
        self.check_OK("/fs_sidebar")

    def test_fs_cut(self):
        self.check_OK("/fs_api/cut?files=001.txt&files=002.txt")
        self.check_OK("/fs_api/clear_clip")

    def test_fs_shell(self):
        self.check_OK("/fs//?mode=shell")

    def test_fs_upload(self):
        self.check_OK("/fs_upload")

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
        self.check_200("/system/settings")
        self.check_200("/system/network_profile?total_size=1024")
        self.check_200("/system/log")
        self.check_200("/system/clipboard-monitor")
        # self.check_200("/system/pydoc")

    def test_api(self):
        self.check_200("/api/check_network")
        self.check_200("/api/getip")
        self.check_200("/api/ipv6")

    def skip_test_sys_storage(self):
        data = json_request("/system/storage?key=unit-test&_format=json", method="POST", data=dict(key="unit-test", value="hello"))
        value = data.get("config").get("value")
        self.assertEqual("hello", value)

        data = json_request("/system/storage?key=unit-test&_format=json")
        value = data.get("config").get("value")
        self.assertEqual("hello", value)

    def test_sys_db_scan(self):
        self.check_OK("/system/db_scan")

    def test_user(self):
        self.check_OK("/system/user")
        self.check_OK("/system/user/list")
        self.check_OK("/system/user?name=admin")

    def test_tools(self):
        self.check_200("/tools/sql")
        self.check_200("/tools/color")

    def test_notfound(self):
        self.check_404("/nosuchfile")

    def test_exec_script(self):
        name = "xnote-unit-test.py"
        content = """print('hello')"""
        test_path = os.path.join(xconfig.SCRIPTS_DIR, name)
        xutils.savetofile(test_path, content)
        result = xutils.exec_script(name)
        self.assertEqual("hello\n", result)

    def test_script_list(self):
        self.check_200("/system/script_admin")

    def test_script_add_remove(self):
        json_request("/system/script/save", method="POST", data=dict(name="xnote-unit-test.py", content="print(123)"))
        out = xutils.exec_script("xnote-unit-test.py", False, False)
        json_request("/system/script/delete?name=xnote-unit-test.py", method="POST")

    def test_script_rename(self):
        path1 = get_script_path("unit-test-1.py")
        path2 = get_script_path("unit-test-2.py")
        xutils.remove(path1, hard = True)
        xutils.remove(path2, hard = True)

        ret = json_request("/system/script/rename?oldname=unit-test-1.py&newname=unit-test-2.py", method="POST")
        self.assertEqual("fail", ret["code"])

        xutils.touch(path1)
        ret = json_request("/system/script/rename?oldname=unit-test-1.py&newname=unit-test-2.py", method="POST")
        self.assertEqual("success", ret["code"])

    def test_report_time(self):
        self.check_200("/api/report_time")

    def test_tts(self):
        self.check_200("/api/tts?content=测试")

    def test_alarm(self):
        self.check_200("/api/alarm/test?repeat=1")

    def test_search(self):
        self.check_200("/search?key=测试")
        self.check_200("/search/search?key=测试")

    def test_search_in_cache(self):
        xconfig.USE_CACHE_SEARCH = True
        self.check_200("/search?key=测试")
        self.check_200("/fs_find?find_key=xnote&path=" + xconfig.DATA_DIR)
        xconfig.USE_CACHE_SEARCH = False
    
    def test_search_calc(self):
        result = json_request("/search?key=1%2B2&_format=json")
        value = result['files'][0]['raw']
        self.assertEqual("3", value)

    def test_search_message(self):
        self.check_200("/message?key=test&category=message")

    def test_search_mute(self):
        self.check_200(xutils.quote_unicode("/search?key=静音"))
        self.assertTrue(xconfig.MUTE_END_TIME != None)

    def test_search_translate(self):
        self.check_200(xutils.quote_unicode("/search?key=翻译test"))

    def test_http_headers(self):
        data = app.request("/api/http_headers", headers=dict(X_TEST=True)).data
        self.assertEqual(True, b"HTTP_X_TEST" in data)

    def test_message_create(self):
        # Py2: webpy会自动把str对象转成unicode对象，data参数传unicode反而会有问题
        response = json_request("/message/save", method="POST", data=dict(content="Xnote-Unit-Test"))
        self.assertEqual("success", response.get("code"))
        data = response.get("data")
        # Py2: 判断的时候必须使用unicode
        self.assertEqual(u"Xnote-Unit-Test", data.get("content"))
        json_request("/message/touch", method="POST", data=dict(id=data.get("id")))
        json_request("/message/delete", method="POST", data=dict(id=data.get("id")))

    def test_message_list(self):
        json_request("/message/list")
        json_request("/message/list?status=created")
        json_request("/message/list?status=suspended")
        # search
        json_request("/message/list?key=1")

    def test_tagname(self):
        self.check_OK("/note/tagname/test")

    def test_taglist(self):
        self.check_OK("/note/taglist")

    def test_document(self):
        self.check_200("/system/modules_info")
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

    def test_code_wiki(self):
        self.check_200("/code/wiki/README.md")

    def test_cron_list(self):
        self.check_200("/system/crontab")

    def test_cron_add_url(self):
        result = json_request("/system/crontab/add", method="POST", 
            data=dict(url="test", tm_wday="*", tm_hour="*", tm_min="*"))
        sched_id = result["data"]["id"]
        self.check_OK("/system/crontab/remove?id={}".format(sched_id))

    def test_cron_add_script(self):
        result = json_request("/system/crontab/add", method="POST", 
            data=dict(script_url="script://test.py", tm_wday="1", tm_hour="*", tm_min="*"))
        sched_id = result["data"]["id"]
        self.check_OK("/system/crontab/remove?id={}".format(sched_id))

    
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

    def test_BaseTextPlugin(self):
        TextPage().render()

    def test_plugin(self):
        code  = '''
class Main:
    def render(self):
        return "hello,world"
        '''
        fpath = os.path.join(xconfig.PLUGINS_DIR, "test.py")
        xutils.savetofile(fpath, code)
        html = request_html("/plugins/test")
        self.assertEqual(b"hello,world", html)

    def test_readbook(self):
        self.check_200("/api/readbook")

    def test_plugins_list(self):
        self.check_200("/plugins_list")

    def test_plugins_new_plugin(self):
        self.check_OK("/plugins_new?input=tpl-test")

    def test_plugins_new_command(self):
        self.check_OK("/plugins_new/command?input=cmd-test")




