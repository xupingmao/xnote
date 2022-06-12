# encoding=utf-8
# Created by xupingmao on 2017/05/23
# @modified 2022/04/17 14:28:57

from .a import *
import os
import xtemplate
import xconfig
import xauth

from xutils import Storage
from xutils import u, dbutil
from xutils import dateutil, dbutil

# cannot perform relative import
try:
    import test_base
except ImportError:
    from tests import test_base

app = test_base.init()
json_request = test_base.json_request
request_html = test_base.request_html
BaseTestCase = test_base.BaseTestCase

MSG_DB = dbutil.get_table("message")


def get_script_path(name):
    return os.path.join(xconfig.SCRIPTS_DIR, name)


def del_msg_by_id(id):
    json_request("/message/delete", method="POST", data=dict(id=id))


def delete_all_messages():
    for record in MSG_DB.iter(limit=-1):
        MSG_DB.delete_by_key(record._key)


class TextPage(xtemplate.BaseTextPlugin):

    def get_input(self):
        return ""

    def get_format(self):
        return ""

    def handle(self, input):
        return "test"


class TestMain(BaseTestCase):

    def test_message_create_and_update(self):
        # Py2: webpy会自动把str对象转成unicode对象，data参数传unicode反而会有问题
        response = json_request(
            "/message/save", method="POST", data=dict(content="Xnote-Unit-Test"))
        self.assertEqual("success", response.get("code"))
        data = response.get("data")
        # Py2: 判断的时候必须使用unicode
        self.assertEqual(u"Xnote-Unit-Test", data.get("content"))
        json_request("/message/touch", method="POST",
                     data=dict(id=data.get("id")))
        
        msg_id = data.get("id")

        update_result = json_request("/message/save", method="POST", data=dict(id=msg_id, content="New Content"))
        self.assertEqual("success", update_result["code"])

        data = dbutil.get(msg_id)

        self.assertEqual("New Content", data["content"])

        json_request("/message/delete", method="POST",
                     data=dict(id=data.get("id")))

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
        response = json_request(
            "/message/save", method="POST", data=dict(content="Xnote-Unit-Test", tag="task"))
        self.assertEqual("success", response.get("code"))
        data = response.get("data")
        msg_id = data['id']

        json_request("/message/finish", method="POST", data=dict(id=msg_id))
        done_result = json_request("/message/list?tag=done")

        self.assertEqual("success", done_result['code'])

        done_list = done_result['data']
        self.assertEqual(2, len(done_list))

        for msg in done_list:
            del_msg_by_id(msg['id'])

    def test_message_key(self):
        response = json_request(
            "/message/save", method="POST", data=dict(content="Xnote-Unit-Test", tag="key"))
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

        month = dateutil.format_date(fmt="%Y-%m")
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

    def test_message_task(self):
        self.check_OK("/message?tag=task")
        self.check_OK("/message?tag=task&action=create")
        self.check_OK("/message?tag=task&filterKey=test")

    def test_task_create_and_done(self):
        # Py2: webpy会自动把str对象转成unicode对象，data参数传unicode反而会有问题
        response = json_request("/message/save", method="POST",
                                data=dict(content="Xnote-Unit-Test-Task", tag="task"))
        self.assertEqual("success", response.get("code"))
        data = response.get("data")
        # Py2: 判断的时候必须使用unicode
        self.assertEqual(u"Xnote-Unit-Test-Task", data.get("content"))

        task_id = data["id"]

        update_result = json_request("/message/status", method="POST",
                                     data=dict(id=task_id, status=100))
        self.assertEqual("success", update_result.get("code"))

        self.check_OK("/message/edit?id=%s" % task_id)

    def test_message_dairy(self):
        self.check_OK("/message/dairy")

    def test_message_search(self):
        delete_all_messages()

        create_data = dict(content="Xnote-Unit-Test")
        response = json_request(
            "/message/save", method="POST", data=create_data)
        self.assertEqual("success", response.get("code"))

        from handlers.message.message import on_search_message
        ctx = Storage(key="xnote", user_name=xauth.current_name(), messages=[])
        on_search_message(ctx)
        # 两条记录（第一个是汇总，第二个是实际数据）
        self.assertEqual(2, len(ctx.messages))
        self.assertEqual("Xnote-Unit-Test", ctx.messages[1].html)

    def test_message_search_page(self):
        self.check_OK("/message?tag=search&key=123")
    
    def test_message_keyword_mark(self):
        response = json_request(
            "/message/save", method="POST", data=dict(content="Xnote-Unit-Test #test#"))
        self.assertEqual("success", response.get("code"))

        result = json_request("/message/keyword", method="POST", data=dict(action="mark", keyword="#test#"))
        self.assertEqual("success", result["code"])

        from handlers.message.message import get_or_create_keyword

        keyword = get_or_create_keyword(xauth.current_name(), "#test#", "127.0.0.1")
        self.assertTrue(keyword.is_marked)

    def test_message_calendar(self):
        self.check_OK("/message/calendar")