# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-28 22:28:31
@LastEditors  : xupingmao
@LastEditTime : 2022-05-28 23:58:17
@FilePath     : /xnote/tests/test_system_sync.py
@Description  : 描述
"""

from .a import *
import xauth
from web.utils import Storage
from xutils import dbutil
from xutils import textutil
from xutils import netutil
from xutils.db.binlog import BinLog

from . import test_base

app = test_base.init()
json_request = test_base.json_request
request_html = test_base.request_html
BaseTestCase = test_base.BaseTestCase

_config_db = dbutil.get_table("cluster_config", type="hash")


class LeaderNetMock:

    def http_get(self, url, charset=None, params=None):
        print("url:{url}, params:{params}".format(**locals()))
        result = dict(code="success",
                      leader=dict(
                          node_id="master",
                          fs_index_count=666,
                          binlog_last_seq=333))
        return textutil.tojson(result)


class TestSystem(BaseTestCase):

    def test_system_sync(self):
        admin_token = xauth.get_user_by_name("admin").token
        _config_db.put("leader.token", admin_token)
        self.check_OK("/system/sync?p=home")
        self.check_OK("/system/sync?p=get_stat&token=" + admin_token)

    def test_system_get_stat(self):
        admin_token = xauth.get_user_by_name("admin").token
        _config_db.put("leader.token", admin_token)
        _config_db.put("leader.host", "http://127.0.0.1:3333")
        resp = json_request("/system/sync?p=get_stat&token=" + admin_token)

        print("get_stat resp:{resp}".format(resp=resp))
        self.assertEqual("success", resp["code"])
        self.assertIsNotNone(resp["leader"])
        self.assertIsNotNone(resp["follower_dict"])

    def test_system_ping(self):
        netutil.set_net_mock(LeaderNetMock())
        admin_token = xauth.get_user_by_name("admin").token
        _config_db.put("leader.token", admin_token)
        _config_db.put("leader.host", "http://127.0.0.1:3333")
        resp = json_request("/system/sync?p=ping&token=" + admin_token)
        print("ping resp:{resp}".format(resp=resp))
        self.assertEqual("success", resp["code"])
        self.assertIsNotNone(resp["data"])
