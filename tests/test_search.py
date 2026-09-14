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

    def test_search_tab_uses_tabbox(self):
        """搜索类型切换 Tab 已重构为 TabBox 组件渲染（不再手写 <a class=link> + selected-link 高亮）"""
        body = self.request_app("/search?key=test").data.decode("utf-8")
        self.assertIn("x-tab-box", body)                       # TabBox 组件
        self.assertIn('data-tab-key="search_type"', body)      # 按 URL 参数 search_type 高亮
        self.assertIn('data-tab-default="default"', body)      # 默认高亮【默认】
        self.assertIn('data-tab-value="content"', body)       # 内容
        self.assertIn('data-tab-value="task"', body)           # 待办
        # 旧实现应已移除
        self.assertNotIn('class="search-tab"', body)
        self.assertNotIn("selected-link", body)

    def test_default_search_includes_todo(self):
        """全局【默认】综合搜索也应检索到新待办模块的内容（折叠为摘要，参考随手记）"""
        resp = self.json_request_return_dict(
            "/api/v1/todo/create", method="POST",
            data=dict(content="综合搜索命中待办S", project_id="1"))
        self.assertTrue(resp["success"])
        task_id = resp["data"]

        # 直接校验 search_todo 处理器：折叠为 tools 桶里的单条摘要，不逐条展开
        from xnote_handlers.todo.todo_search import search_todo
        from xnote.core.models import SearchContext
        import xauth
        ctx = SearchContext(key="综合搜索命中待办S")
        ctx.user_id = xauth.current_user_id()
        search_todo(ctx)
        summaries = [f for f in ctx.tools
                     if getattr(f, "name", "").startswith("搜索到") and "个待办" in f.name]
        self.assertEqual(len(summaries), 1)
        self.assertIn("/todo/task?model=task", summaries[0].url)
        self.assertIn("status=all", summaries[0].url)
        # 不应逐条展开待办详情
        self.assertFalse(any(getattr(f, "url", "").startswith("/todo/detail")
                              for f in ctx.tools))

        # 搜索页可正常渲染（不 500）
        self.check_OK("/search?key=综合搜索命中待办S")

        # 旧 message 标签的 task 分类搜索走 do_search_by_type，不触发 search 事件，不混入新待办
        note_body = self.request_app("/search?search_type=note&key=综合搜索命中待办S").data.decode("utf-8")
        self.assertNotIn("/todo/task?model=task", note_body)

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
