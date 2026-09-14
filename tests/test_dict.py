# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-01 12:52:24
@LastEditors  : xupingmao
@LastEditTime : 2022-05-01 15:09:21
@FilePath     : /xnote/tests/test_dict.py
"""

from .test_base import json_request, json_request_return_dict, BaseTestCase
from .test_base import init as init_app
from xnote.core import xauth
from xnote_handlers.dict import dict_dao

app = init_app()

class TestMain(BaseTestCase):

    def test_dict(self):
        params = dict(
            key="name",
            value="姓名",
            dict_type=dict_dao.DictTypeEnum.public.int_value,
        )        
        resp = json_request_return_dict("/api/v1/dict/create", method = "POST", data = params)
        assert resp["success"] == True
        
        self.check_OK("/note/dict")
        self.check_OK("/dict/search?key=name")
    
    def test_dict_relevant(self):
        params = dict(
            key="test",
            value="test1 test2",
            dict_type=dict_dao.DictTypeEnum.relevant.int_value,
        )
        resp1 = json_request_return_dict("/api/v1/dict/create", method = "POST", data = params)
        self.assertEqual("success", resp1["code"])

        words = dict_dao.get_relevant_words("test")
        assert words == ["test1", "test2"]

    def test_dict_list(self):
        self.check_OK("/note/dict")
        self.check_OK("/note/dict?dict_type=1")
        self.check_OK("/note/dict?dict_type=2")
        self.check_OK("/note/dict?dict_type=3")
    
    def test_dict_page_edit(self):
        dict_item = dict_dao.DictDO()
        dict_item.dict_type = dict_dao.DictTypeEnum.personal.int_value
        dict_item.key = "test"
        dict_item.value = "test value"
        dict_item.user_id = xauth.current_user_id()
        dict_id = dict_dao.DictPersonalDao.create(dict_item)
        self.check_OK(f"/note/dict?action=page_edit&dict_id={dict_id}")
