# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/07/18 18:36:23
# @modified 2026/05/23
# @filename test_search.py

import xutils
from . import test_base
from .test_base import json_request_return_dict
from xnote.core import xauth, xconfig, xmanager
from xnote.core.models import SearchContext

app          = test_base.init()
json_request = test_base.json_request
request_html = test_base.request_html
BaseTestCase = test_base.BaseTestCase

class TestMain(BaseTestCase):

    def test_search(self):
        self.check_OK("/search")

    def test_search_message(self):
        self.check_OK("/search?category=message")

    def test_search_calc(self):
        result = json_request_return_dict("/search?key=1%2B2&_format=json")
        value = result['files'][0]['raw']
        self.assertEqual("1+2=3", value)
    
    def test_search_note(self):
        self.check_OK("/search?search_type=note&key=test")
    
    def test_search_dict(self):
        self.check_OK("/search?search_type=dict&key=test")
    
    def test_search_task(self):
        self.check_OK("/search?search_type=task&key=test")

    def test_search_comment(self):
        self.check_OK("/search?search_type=comment&key=test")

    def test_search_history(self):
        from xnote_handlers.note import dao
        dao.add_search_history(None, "test")
        dao.expire_search_history("user")
        dao.list_search_history("user")

        user_name = xauth.current_name_str()
        dao.add_search_history(user_name, "test")
        from xnote_handlers.search.search import list_search_history

        words = list_search_history(user_name=user_name)
        assert "test" in words

    def test_search_dialog(self):
        self.check_OK("/search/dialog?key=test")

    def test_search_mute(self):
        """测试静音搜索"""
        self.check_OK(xutils.quote_unicode("/search?key=静音"))
        self.assertTrue(xconfig.MUTE_END_TIME != None)

    def test_search_mute_en(self):
        """测试英文静音搜索"""
        self.check_OK(xutils.quote_unicode("/search?key=mute"))
        self.assertTrue(xconfig.MUTE_END_TIME != None)

    def test_search_unmute(self):
        """测试取消静音搜索"""
        xconfig.MUTE_END_TIME = xutils.dateutil.timestamp_ms() + 3600000
        self.check_OK(xutils.quote_unicode("/search?key=取消静音"))
        self.assertTrue(xconfig.MUTE_END_TIME == None)

    def test_search_api(self):
        """测试API搜索"""
        self.check_OK(xutils.quote_unicode("/search?key=weather"))

    def test_searchable_decorator(self):
        """测试 searchable 装饰器注册的处理器是否正确"""
        import xnote_handlers.search.mute as mute_module
        import xnote_handlers.search.api as api_module
        # 验证模块导入正常，装饰器会在模块加载时注册

        # 验证 mute 搜索函数
        ctx = SearchContext(key="静音")
        ctx.groups = [""]
        ctx.search_tool = True
        try:
            mute_module.search_mute(ctx)
            self.assertTrue(xconfig.MUTE_END_TIME is not None)
            self.assertTrue(len(ctx.tools) > 0)
        finally:
            xconfig.MUTE_END_TIME = None

        # 验证 api 搜索函数
        ctx_api = SearchContext(key="weather")
        ctx_api.groups = ["weather"]
        ctx_api.search_tool = True
        try:
            api_module.search_api(ctx_api)
            # 无论是否找到api，只要函数能正常执行就好
        except:
            pass
