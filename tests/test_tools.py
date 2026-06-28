# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-01 12:52:24
@LastEditors  : xupingmao
@LastEditTime : 2022-05-01 15:09:21
@FilePath     : /xnote/tests/test_dict.py
"""

from .test_base import json_request, json_request_return_dict, BaseTestCase, request_html
from .test_base import init as init_app
from xnote.core import xauth
from xnote_handlers.dict import dict_dao

app = init_app()

class TestMain(BaseTestCase):

    def test_encode(self):
        self.check_OK("/tools/encode?tab=BASE64&type=base64")
        result = self.json_request_return_dict("/tools/encode?event_type=click&input=1234&encode_type=base64")
        assert result.get_bool("success")

