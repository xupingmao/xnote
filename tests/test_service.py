# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-04-04 00:01:38
@LastEditors  : xupingmao
@LastEditTime : 2024-07-06 16:20:57
@FilePath     : /xnote/tests/test_service.py
@Description  : 描述
"""
import time
from . import test_base
from xnote.core import xtables
from xnote.service import DatabaseLockService
from xnote.service import TagBindService
from xnote.service import TagTypeEnum

app = test_base.init()

class TestMain(test_base.BaseTestCase):
    """测试管理后台的功能"""

    db = xtables.get_table_by_name("t_lock")

    def get_lock_record_by_key(self, lock_key=""):
        return self.db.select_first(where=dict(lock_key=lock_key))    
    
    def test_lock_service_conflict(self):
        lock_key = "test_conflict"

        lock1 = DatabaseLockService.lock(lock_key)
        assert self.get_lock_record_by_key(lock_key) != None

        try:
            lock2 = DatabaseLockService.lock(lock_key)
            assert False
        except:
            assert True
        
        lock1.release()

        assert self.get_lock_record_by_key(lock_key) == None
    
    def test_lock_and_free(self):
        lock_key = "test_lock_and_free"
        with DatabaseLockService.lock(lock_key):
            assert self.get_lock_record_by_key(lock_key) != None
            print("do some work")
        
        assert self.get_lock_record_by_key(lock_key) == None

    def test_lock_timeout(self):
        lock_key = "test_lock_timeout"
        with DatabaseLockService.lock(lock_key, timeout_seconds=0.1):
            assert self.get_lock_record_by_key(lock_key) != None
            time.sleep(0.5)
            t2 = DatabaseLockService.lock(lock_key)
            assert t2.got_lock
            current_lock = self.get_lock_record_by_key(lock_key)
            assert current_lock != None
            assert current_lock.lock_token == t2.lock_token
        
        current_lock = self.get_lock_record_by_key(lock_key)
        assert current_lock != None


    def test_tag_service(self):
        service = TagBindService(tag_type=TagTypeEnum.msg_tag)
        user_id = 1
        target_id = 1234
        # delete all tag binds
        service.bind_tags(user_id=user_id, target_id=target_id, tags=[])
        count = service.count_user_tag(user_id=user_id, target_id=target_id)
        assert count == 0

        service.bind_tags(user_id=user_id, target_id=target_id, tags=["tag1", "tag2"])
        count = service.count_user_tag(user_id=user_id, target_id=target_id)
        assert count == 2
        bindlist = service.get_by_target_id(user_id=user_id, target_id=target_id)
        bindlist.sort(key = lambda x:x.tag_code)
        assert len(bindlist) == 2
        assert bindlist[0].tag_code == "tag1"
        assert bindlist[1].tag_code == "tag2"

    def test_tag_service_with_second_type(self):
        service = TagBindService(tag_type=TagTypeEnum.msg_tag)
        user_id = 1
        target_id = 1234
        type1 = 1

        # delete all tag binds
        service.bind_tags(user_id=user_id, target_id=target_id, tags=[])
        count = service.count_user_tag(user_id=user_id, target_id=target_id)
        assert count == 0

        service.bind_tags(user_id=user_id, target_id=target_id, tags=["tag1", "tag2"], second_type=type1)
        count = service.count_user_tag(user_id=user_id, target_id=target_id, second_type=type1)
        assert count == 2
        bindlist = service.get_by_target_id(user_id=user_id, target_id=target_id, second_type=type1)
        bindlist.sort(key = lambda x:x.tag_code)
        assert len(bindlist) == 2
        assert bindlist[0].tag_code == "tag1"
        assert bindlist[0].second_type == type1
        assert bindlist[1].tag_code == "tag2"
        assert bindlist[1].second_type == type1
