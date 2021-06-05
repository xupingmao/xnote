# encoding=utf-8
# Created by xupingmao on 2017/05/23
# @modified 2021/06/05 16:31:08

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
from xutils import dateutil

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

def del_msg_by_id(id):
    json_request("/message/delete", method="POST", data=dict(id=id))

class TextPage(xtemplate.BaseTextPlugin):

    def get_input(self):
        return ""

    def get_format(self):
        return ""

    def handle(self, input):
        return "test"

class TestMain(BaseTestCase):

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
        json_request("/message/list?tag=file")
        json_request("/message/list?tag=link")
        json_request("/message/list?tag=todo")
        # search
        json_request("/message/list?key=1")

        self.check_OK("/message/list?format=html")

    def test_message_finish(self):
        response = json_request("/message/save", method="POST", data=dict(content="Xnote-Unit-Test", tag="task"))
        self.assertEqual("success", response.get("code"))
        data = response.get("data")
        msg_id = data['id']

        json_request("/message/finish", method="POST", data=dict(id = msg_id))
        done_result = json_request("/message/list?tag=done")

        self.assertEqual("success", done_result['code'])

        done_list = done_result['data']
        self.assertEqual(2, len(done_list))

        for msg in done_list:
            del_msg_by_id(msg['id'])

    def test_message_key(self):
        response = json_request("/message/save", method="POST", data=dict(content="Xnote-Unit-Test", tag="key"))
        self.assertEqual("success", response.get("code"))
        data = response.get("data")
        msg_id = data['id']

        key_result = json_request("/message/list?tag=key")
        self.assertEqual("success", key_result['code'])

        key_list = key_result['data']
        self.assertEqual(1, len(key_list))

        del_msg_by_id(msg_id)

    def test_message_stat(self):
        result = json_request("/message/stat")
        self.assertTrue(result.get("cron_count") != None)

    def test_message_todo(self):
        self.check_OK("/message/todo")
        self.check_OK("/message/done")

    def test_list_by_month(self):
        self.check_OK("/message/date?date=2021-05")
        
    def test_list_by_day(self):
        # 创建一条记录
        response = json_request("/message/save", method="POST", 
            data=dict(content="Xnote-Unit-Test", tag="log"))

        month = dateutil.format_date(fmt = "%Y-%m")
        date = dateutil.format_date()
        self.check_OK("/message/list_by_day?date=" + month)
        self.check_OK("/message?date=" + date)
        
    def test_message_refresh(self):
        self.check_OK("/message/refresh")

    def test_message_task_tags(self):
        # 创建一条记录
        response = json_request("/message/save", method="POST", 
            data=dict(content="#TEST# Xnote-Unit-Test", tag="task"))

        self.check_OK("/message?tag=task_tags")





