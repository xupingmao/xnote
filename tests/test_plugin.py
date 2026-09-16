# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/07/18 18:36:23
# @modified 2021/07/18 19:45:09
# @filename test_search.py

from . import test_base
from .test_base import json_request_return_dict
from xnote.core import xauth
from xnote.core import xtables
from xnote_handlers.plugin.dao import add_visit_log, delete_visit_log
from xnote.plugin import db as plugin_db

app          = test_base.init()
json_request = test_base.json_request
request_html = test_base.request_html
BaseTestCase = test_base.BaseTestCase

class TestMain(BaseTestCase):

    def test_plugin_list(self):
        self.check_OK("/plugin_list")

    def test_table(self):
        self.check_OK("/test/example/table?name=table")

    def test_contribution_calendar(self):
        self.check_OK("/test/example/calendar?name=calendar")

    def test_list(self):
        self.check_OK("/test/example/list?name=list")

    def test_list_delete_link_is_red(self):
        # ListPlugin 示例页的【删除】操作链接使用红色
        body = self.request_app("/test/example/list_plugin").data.decode("utf-8")
        self.assertRegex(body, r'<a class="red"[^>]*data-url="\?action=delete')

    def test_list_plugin(self):
        self.check_OK("/test/example/list_plugin")

    def test_tag_example(self):
        # Tag 示例页展示新增的浅红/浅紫标签
        body = self.request_app("/test/example?name=tag").data.decode("utf-8")
        self.assertIn("lightred标签", body)
        self.assertIn("lightpurple标签", body)

    def test_form_example(self):
        # Form 示例页：页面表单 + 查询表单 + 弹窗表单入口
        body = self.request_app("/test/example/form").data.decode("utf-8")
        self.assertIn("页面表单", body)
        self.assertIn("查询表单", body)
        self.assertIn("打开弹窗表单", body)
        # 弹窗表单使用 DialogForm 组件触发（xnote.table.handleEditForm + data-url）
        self.assertIn("xnote.table.handleEditForm(this)", body)
        self.assertIn('data-url="/test/example/form?action=edit"', body)
        # 静态表单渲染了图片上传行（验证 common-form.css 的 form-upload 样式）
        self.assertIn("form-upload-row", body)
        # 静态表单使用 page_edit 类型（页面内联编辑表单，static 定位，避免弹窗 edit 的 absolute 错位）
        self.assertIn("page-edit-form", body)
        # 查询表单按钮
        self.assertIn("查询数据", body)
        # 不应出现重复的面包屑（开发 / Form示例）：framework 已渲染一个 plugin-head 面包屑，
        # 旧的 example_nav.html 又会渲染一个，需用 example_nav_tab.html 避免重复
        self.assertEqual(body.count('class="link2 path-link"'), 1)

    def test_form_example_edit_dialog(self):
        # 弹窗表单：action=edit 返回可注入对话框的表单 HTML
        body = self.request_app("/test/example/form?action=edit").data.decode("utf-8")
        self.assertIn("弹窗表单示例", body)
        self.assertIn('class="x-form"', body)

    def test_plugin_visit(self):
        delete_visit_log(user_name="admin", url="/test")
        assert add_visit_log(user_name="admin", url="/test") == 1
        assert add_visit_log(user_name="admin", url="/test") == 2

    def test_plugin_manage(self):
        self.check_OK("/plugin_manage")
        
    def test_plugin_db(self):
        with plugin_db.create_plugin_table(table_name="plugin_test") as manager:
            manager.add_column("name", "text", default_value="", comment="name")
            manager.add_column("age", "int", default_value=0)
        
        db = xtables.get_table_by_name("plugin_test")
        db.insert(name = "test", age = 20)
        results = db.select()
        print(f"results={results}")
        assert len(results) > 0

