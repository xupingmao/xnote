# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-28 22:28:31
@LastEditors  : xupingmao
@LastEditTime : 2024-06-30 17:02:14
@FilePath     : /xnote/tests/test_system_sync.py
@Description  : 描述
"""

import os
import re
import json

from .a import *
from urllib.parse import urlparse, parse_qs, unquote

from xutils import dbutil, fsutil
from xutils import textutil
from xutils import netutil
from xutils import dateutil
from xutils import jsonutil
from xutils import webutil
from xnote.core import xauth
from xnote.core import xconfig
from xnote.core import xnote_event
from . import test_base
from xnote_handlers.system.system_sync.node_follower import DBSyncer
from xnote_handlers.system.system_sync.dao import ClusterConfigDao
from xnote_handlers.system.system_sync.models import LeaderStat, ListDBResponse
from xnote_handlers.system.system_sync import system_sync_proxy
from xutils.db.binlog import BinLog, BinLogOpType, BinLogRecord
from xnote.open_api import BaseResponse, FailedResponse, SuccessResponse
from xnote.core.test_env import TestEnv

app = test_base.init()
json_request = test_base.json_request
json_request_return_dict = test_base.json_request_return_dict
request_html = test_base.request_html
BaseTestCase = test_base.BaseTestCase

from xnote.open_api import client
from xnote.service.system_meta_service import SystemMetaService
from xnote.service.system_meta_service import SystemMetaEnum

def init_open_api():
    app_info = dict(
        app_name = "test",
        app_key = xconfig.WebConfig.cluster_node_id,
    )

    data = dict(
        action = "save",
        data = json.dumps(app_info)
    )
    json_request("/system/sync/app", method="POST", data=data)
    SystemMetaEnum.leader_base_url.save_meta("http://127.0.0.1:1234")

DBSyncer.MAX_LOOPS = 100
DBSyncer.FULL_SYNC_MAX_LOOPS = 100


init_open_api()

def get_test_access_token(readonly=False):
    from xnote_handlers.system.system_sync.models import SystemSyncToken
    from xnote_handlers.system.system_sync.dao import SystemSyncTokenDao
    follower_name = "test"
    token_info = SystemSyncTokenDao.get_by_holder(follower_name)
    if token_info == None:
        token_info = SystemSyncToken()
        token_info.token_holder = follower_name

    if readonly:
        return token_info.token

    token_info.token = textutil.create_uuid()
    unixtime = dateutil.get_seconds()
    token_info.expire_time = dateutil.format_datetime(unixtime+3600)
    SystemSyncTokenDao.upsert(token_info)
    return token_info.token

class LeaderNetMock:

    def http_get(self, url, charset=None, params=None):
        print("url:{url}, params:{params}".format(**locals()))
        access_token = ""

        if params != None:
            url = netutil._join_url_and_params(url, params)
            access_token = params.get("token", "")

        if access_token == "":
            struct_url = netutil.parse_url(url)
            access_token = struct_url.get_single_param("token")

        if "get_stat" in url:
            assert access_token == get_test_access_token(readonly=True)
            return self.http_get_stat()

        if "refresh_token" in url:
            return self.refresh_token(url)

        raise Exception("unsupported url:%s" % url)

    def refresh_token(self, url):
        from xnote_handlers.system.system_sync.dao import SystemSyncTokenDao
        follower_name = "test"
        token_info = SystemSyncTokenDao.get_by_holder(follower_name)
        result = webutil.SuccessResult(token_info)
        return jsonutil.tojson(result)

    def http_get_stat(self):
        leader_stat = LeaderStat()
        leader_stat.access_token = get_test_access_token(readonly=True)
        return textutil.tojson(leader_stat)

class TestSystemSync(BaseTestCase):

    def get_access_token(self):
        return get_test_access_token()
    
    def get_leader_token(self):
        token = textutil.create_uuid()
        ClusterConfigDao.put_leader_token(token)
        return token
    
    def init_leader_config(self):
        token = textutil.create_uuid()
        ClusterConfigDao.put_leader_token(token)
        ClusterConfigDao.put_leader_host("http://127.0.0.1:3333")

    def test_system_sync(self):
        access_token = self.get_access_token()
        self.check_OK("/system/sync?p=home")
        self.check_OK("/system/sync?p=get_stat&token=" + access_token)

    def test_system_get_stat(self):
        self.init_leader_config()
        admin_token = self.get_access_token()
        resp = json_request_return_dict("/system/sync?p=get_stat&token=" + admin_token)

        print("get_stat resp:{resp}".format(resp=resp))
        self.assertEqual("success", resp["code"])
        self.assertIsNotNone(resp["leader"])
        self.assertIsNotNone(resp["follower_dict"])

    def test_system_ping(self):
        netutil.set_net_mock(LeaderNetMock())
        try:
            self.init_leader_config()
            admin_token = self.get_access_token()
            resp = json_request_return_dict("/system/sync?p=ping&token=" + admin_token)
            print("ping resp:{resp}".format(resp=resp))
            self.assertEqual("success", resp["code"])
            self.assertIsNotNone(resp["data"])
        finally:
            netutil.set_net_mock(None)

    def fast_backup(self):
        if TestEnv.has_backup:
            return
        
        TestEnv.is_test = True
        TestEnv.skip_backup = False
        self.check_OK("/system/backup")
        TestEnv.skip_backup = True
        TestEnv.has_backup = True

    def test_system_sync_db_full(self):
        self.fast_backup()
        from xnote_handlers.system.system_sync.system_sync_controller import FollowerInstance
        netutil.set_net_mock(LeaderNetMock())
        binlog_obj = BinLog.get_instance()

        try:
            self.get_access_token()
            self.init_leader_config()

            FollowerInstance._debug = True
            db_syncer = FollowerInstance.db_syncer
            db_syncer.debug = True
            db_syncer.put_db_sync_state("full")

            self.fast_backup()
            max_id = binlog_obj.get_max_id()
            assert isinstance(max_id, int)
            
            # 全量同步
            FollowerInstance.sync_db_from_leader()

            self.assertEqual(db_syncer.get_db_sync_state(), "binlog")
            # 备份前第一步进行binlog id备份，但是备份完成后会插入一条新的文件索引记录，所以这里是max_id - 1
            self.assertEqual(db_syncer.get_binlog_last_seq(), max_id - 1)
        finally:
            netutil.set_net_mock(None)

    def test_system_sync_db_binlog(self):
        from xnote_handlers.system.system_sync.system_sync_controller import FollowerInstance
        from xnote_handlers.system.system_sync.system_sync_indexer import on_fs_upload
        netutil.set_net_mock(LeaderNetMock())

        binlog_instance = BinLog.get_instance()

        self.fast_backup()

        try:
            self.get_access_token()
            self.init_leader_config()

            current_seq = binlog_instance.get_max_id()
            kv_db = dbutil.get_table("test")

            for i in range(50):
                record = dict(name = "test", age = 20 + i)
                kv_db.insert(record)
            
            SystemMetaEnum.dev_mode.save_meta("0")
            SystemMetaEnum.dev_mode.save_meta("1")
            
            upload_event = xnote_event.FileUploadEvent()
            upload_event.fpath = "./tmp/a.txt"
            upload_event.user_id = 0
            on_fs_upload(upload_event)
            

            FollowerInstance._debug = True
            db_syncer = FollowerInstance.db_syncer
            db_syncer.debug = True
            db_syncer.put_db_sync_state("binlog")
            db_syncer.put_binlog_last_seq(current_seq + 10)
            
            # 增量同步
            FollowerInstance.sync_db_from_leader()

            self.assertEqual(db_syncer.get_binlog_last_seq(), binlog_instance.get_max_id())
            self.assertEqual(db_syncer.get_db_sync_state(), "binlog")
        finally:
            netutil.set_net_mock(None)


    def test_system_sync_db_broken(self):
        self.fast_backup()
        from xnote_handlers.system.system_sync.system_sync_controller import FollowerInstance

        binlog = BinLog.get_instance()

        self.get_access_token()
        self.init_leader_config()
        self.fast_backup()
        FollowerInstance._debug = True
        FollowerInstance.db_syncer.put_db_sync_state("binlog")
        FollowerInstance.db_syncer.put_binlog_last_seq(binlog.get_max_id() + 10000)
        result = FollowerInstance.db_syncer.sync_by_binlog(FollowerInstance.get_client())
        self.assertEqual(result, "sync_by_full")
    
    def test_is_token_active(self):
        from xnote_handlers.system.system_sync.system_sync_controller import FollowerInstance
        result = """
        {
            "code": "success",
            "timestamp": 1654227462,
            "system_version": "v2.9-dev-2022.06.03",
            "admin_token": "fake-token",
            "fs_index_count": 10960,
            "follower_dict": {
                "127.0.0.1:2222#follower": {
                    "ping_time_ts": 1654227411.8821118,
                    "client_id": "127.0.0.1:2222#follower",
                    "connected_time": "2022-06-03 11:20:16",
                    "connected_time_ts": 1654226416.2453492,
                    "ping_time": "2022-06-03 11:36:51",
                    "fs_sync_offset": "00000001654174803260#/data/path/to/file.txt",
                    "fs_index_count": 10960,
                    "admin_token": "fake-token",
                    "node_id": "follower",
                    "url": "127.0.0.1:2222#follower"
                }
            }
        }
        """
        result_dict = textutil.parse_json(result)
        result_obj = LeaderStat.from_dict(result_dict)
        assert result_obj != None
        result_obj.access_token = self.get_access_token()
        FollowerInstance.update_ping_result(result_obj)
        self.assertTrue(FollowerInstance.is_token_active())

    def test_build_fs_sync_index(self):
        self.check_OK("/system/sync?p=build_index")
    
    def test_list_files(self):
        from xnote_handlers.system.system_sync import system_sync_indexer

        testfile_1 = os.path.join(xconfig.UPLOAD_DIR, "fs_sync_test_01.txt")
        testfile_2 = os.path.join(xconfig.UPLOAD_DIR, "fs_sync_test_02.txt")
        fsutil.touch(testfile_1)
        fsutil.touch(testfile_2)

        manager = system_sync_indexer.FileSyncIndexManager()
        manager.build_full_index()
        result = manager.list_files(last_id=0)
        self.assertTrue(len(result) > 0)
    
    def test_leader_list_binlog(self):
        from xnote_handlers.system.system_sync.system_sync_controller import LeaderInstance
        from xutils.db.binlog import BinLog
        binlog = BinLog.get_instance()
        binlog.set_max_size(1000)
        binlog.set_enabled(True)

        for i in range(20):
            binlog.add_log("put", "test", i)
        last_seq = binlog.last_seq - 10
        result = LeaderInstance.list_binlog(last_seq=last_seq, limit=20)
        assert result.success == True

    def test_system_sync_binlog(self):
        self.check_OK("/system/sync/binlog")

    def test_leader_list_file_binlog(self):
        from xnote_handlers.system.system_sync.system_sync_controller import LeaderInstance
        from xnote_handlers.system.system_sync.system_sync_indexer import on_fs_upload, FileIndexCheckManager
        from xutils.db.binlog import BinLog, BinLogOpType
        binlog = BinLog.get_instance()
        binlog.set_max_size(1000)
        binlog.set_enabled(True)

        fsutil.touch("./tmp/a.txt")

        upload_event = xnote_event.FileUploadEvent()
        upload_event.fpath = "./tmp/a.txt"
        upload_event.user_id = 0
        on_fs_upload(upload_event)

        last_seq = binlog.last_seq
        result = LeaderInstance.list_binlog(last_seq=last_seq, limit=20)
        assert result.success == True
        assert isinstance(result.data, list)
        assert len(result.data) == 1
        assert result.data[0].op_type == BinLogOpType.file_upload
        assert result.data[0].value_obj["fpath"] == upload_event.fpath
        assert result.data[0].value_obj["ftype"] == "txt"

        check_manager = FileIndexCheckManager()
        check_manager.run_step()

    def test_system_meta(self):
        info_key = "config.test"
        SystemMetaService.save_meta(info_key, "1")
        value = SystemMetaService.get_meta_value(info_key)
        assert value == "1"
        SystemMetaService.save_meta(info_key, "2")
        value = SystemMetaService.get_meta_value(info_key)
        assert value == "2"

    def test_open_api(self):
        init_open_api()
        request = client.BaseRequest()
        request.data = "hello"
        request.api_name = "test.ping"
        print(request)
        resp = client.invoke_remote_api(request)
        print(resp)
        assert resp.success
        assert resp.data == "success"


