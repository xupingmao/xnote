# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/07/18 18:36:23
# @modified 2021/07/18 19:45:09
# @filename test_search.py

import os
import tempfile
import xutils

from . import test_base
from .test_base import json_request_return_dict
from xnote.core import xauth
from xnote.core import xconfig
from xnote.core import xtables
from xutils import fsutil
from xnote_handlers.plugin.dao import add_visit_log, delete_visit_log
from xnote.plugin import load_plugin_file
from xnote.plugin import db as plugin_db

app          = test_base.init()
json_request = test_base.json_request
request_html = test_base.request_html
BaseTestCase = test_base.BaseTestCase

class TestMain(BaseTestCase):

    def test_plugin_list(self):
        self.check_OK("/plugin_list")

    def test_table(self):
        self.check_OK("/examples/table?name=table")

    def test_contribution_calendar(self):
        self.check_OK("/examples/calendar?name=calendar")

    def test_list(self):
        self.check_OK("/examples/list_view?name=list_view")

    def test_list_view_multi_line_item(self):
        # ListView 示例页展示 2行 / 3行 item：icon 与标题同行（inline 内容），
        # 后续行渲染为 list-item-line：2行item 2个(1 line) + 3行item 2个(2 lines) = 6 个子行
        body = self.request_app("/examples/list_view").data.decode("utf-8")
        self.assertIn("ListView: 2行item", body)
        self.assertIn("ListView: 3行item", body)
        self.assertIn("说明：这里是第二行内容", body)
        self.assertEqual(body.count('class="list-item-line'), 6)

    def test_list_delete_link_is_red(self):
        # ListPlugin 示例页的【删除】操作链接使用红色
        body = self.request_app("/examples/list_plugin").data.decode("utf-8")
        self.assertRegex(body, r'<a class="red"[^>]*data-url="\?action=delete')

    def test_list_plugin(self):
        self.check_OK("/examples/list_plugin")

    def test_router_plugin_example(self):
        # 路由插件示例页可访问，action=hello 命中 HelloView
        self.check_OK("/examples/router")
        body = self.request_app("/examples/router?action=hello").data.decode("utf-8")
        self.assertIn("HelloView", body)

    def test_router_plugin_dispatch(self):
        # action=search.* 正则匹配，子视图自己从 query 取业务参数
        body = self.request_app("/examples/router?action=search&key=abc").data.decode("utf-8")
        self.assertIn("SearchView", body)
        self.assertIn("key=abc", body)
        # 未命中任何路由时展示兜底视图
        body = self.request_app("/examples/router").data.decode("utf-8")
        self.assertIn("DefaultView", body)

    def test_tag_example(self):
        # Tag 示例页展示新增的浅红/浅紫标签
        body = self.request_app("/examples/tag").data.decode("utf-8")
        self.assertIn("lightred标签", body)
        self.assertIn("lightpurple标签", body)
        # 分段选择器风格（单选/多选两个案例）
        self.assertIn("tag-select segment-style", body)
        self.assertIn("分段选择器（单选）", body)
        self.assertIn("分段选择器（多选）", body)

    def test_switch_example(self):
        # Switch 示例页：渲染出各尺寸的开关，且默认关闭的不带 active
        body = self.request_app("/examples/switch").data.decode("utf-8")
        self.assertIn("x-switch", body)
        self.assertIn("switch-sm", body)
        self.assertIn("switch-lg", body)
        self.assertIn("默认开启", body)

    def test_switch_example_submit(self):
        # 开关在表单里提交：隐藏域是值的唯一来源，未提交时取到 off_value
        url = "/examples/switch"
        body = self.request_app(url, method="POST",
                                data=dict(enabled="true", notify="false")).data.decode("utf-8")
        self.assertIn("enabled=true", body)
        self.assertIn("notify=false", body)
        # 提交上来的值回填到开关的选中态
        self.assertIn('value="true"', body)

    def test_form_example(self):
        # Form 示例页：页面表单 + 查询表单 + 弹窗表单入口
        body = self.request_app("/examples/form").data.decode("utf-8")
        self.assertIn("页面表单", body)
        self.assertIn("查询表单", body)
        self.assertIn("打开弹窗表单", body)
        # 弹窗表单使用 DialogForm 组件触发（xnote.table.handleEditForm + data-url）
        self.assertIn("xnote.table.handleEditForm(this)", body)
        self.assertIn('data-url="/examples/form?action=edit"', body)
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
        body = self.request_app("/examples/form?action=edit").data.decode("utf-8")
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


class TestPluginManageDelete(BaseTestCase):
    """插件管理页的删除功能"""

    PLUGIN_NAME = "unit_test_plugin_manage.py"

    PLUGIN_CODE = '''# -*- coding:utf-8 -*-
# @api-level 2.8
# @title 插件管理单元测试
# @description 仅用于测试插件删除
# @category test
from xnote.core.xtemplate import BasePlugin

class Main(BasePlugin):
    def render(self):
        return "unit-test-plugin"
'''

    def setUp(self):
        # 删除是软删除(移动到回收站), 把回收站重定向到临时目录, 避免写脏 testdata/trash
        self._trash = fsutil.FileUtilConfig.trash_dir
        self.tmp = tempfile.TemporaryDirectory()
        fsutil.FileUtilConfig.trash_dir = os.path.join(self.tmp.name, "trash")
        os.makedirs(fsutil.FileUtilConfig.trash_dir)

        # 预热: 首个请求会触发插件目录的懒加载(会重建 PLUGINS_DICT), 先消耗掉
        self.request_app("/plugin_manage")

        self.fpath = os.path.join(xconfig.PLUGINS_DIR, self.PLUGIN_NAME)
        xutils.savetofile(self.fpath, self.PLUGIN_CODE)
        load_plugin_file(self.fpath)

    def tearDown(self):
        xconfig.PLUGINS_DICT.pop(self.PLUGIN_NAME, None)
        if os.path.exists(self.fpath):
            os.remove(self.fpath)
        fsutil.FileUtilConfig.trash_dir = self._trash
        self.tmp.cleanup()

    def list_trash_files(self):
        result = []
        for root, _, files in os.walk(fsutil.FileUtilConfig.trash_dir):
            result.extend(files)
        return result

    def test_delete_action_rendered_in_page(self):
        # 表格里渲染出删除按钮(确认操作 + 红色)
        body = self.request_app("/plugin_manage").data.decode("utf-8")
        self.assertIn(self.PLUGIN_NAME, body)
        self.assertRegex(body, r'data-url="\?action=delete&(amp;)?plugin_name=unit_test_plugin_manage\.py"')
        self.assertIn("xnote.table.handleConfirmAction", body)
        self.assertIn("btn danger", body)

    def test_delete_plugin(self):
        self.assertIn(self.PLUGIN_NAME, xconfig.PLUGINS_DICT)
        url = "/plugin_manage?action=delete&plugin_name=" + xutils.quote(self.PLUGIN_NAME)

        resp = json_request_return_dict(url)
        self.assertTrue(resp.get("success"))
        self.assertIn("已删除", resp.get("message"))

        # 原件已不在插件目录
        self.assertFalse(os.path.exists(self.fpath))
        # 软删除: 文件落到了回收站
        self.assertEqual(1, len(self.list_trash_files()))
        # 内存中同步移除
        self.assertNotIn(self.PLUGIN_NAME, xconfig.PLUGINS_DICT)
        # 插件地址立即失效
        body = self.request_app("/plugin/" + self.PLUGIN_NAME).data.decode("utf-8")
        self.assertIn("不存在", body)

    def test_delete_plugin_without_name(self):
        resp = json_request_return_dict("/plugin_manage?action=delete")
        self.assertFalse(resp.get("success"))
        self.assertIn("plugin_name", resp.get("message"))

    def test_delete_plugin_not_exists(self):
        resp = json_request_return_dict("/plugin_manage?action=delete&plugin_name=not_exists_plugin.py")
        self.assertFalse(resp.get("success"))
        self.assertIn("不存在", resp.get("message"))

    def test_delete_builtin_plugin_refused(self):
        # 内置工具也在 PLUGINS_DICT 中, 但不允许删除
        builtin_name = "/note/stat"
        self.assertIn(builtin_name, xconfig.PLUGINS_DICT)

        url = "/plugin_manage?action=delete&plugin_name=" + xutils.quote(builtin_name)
        resp = json_request_return_dict(url)
        self.assertFalse(resp.get("success"))
        self.assertIn("内置插件", resp.get("message"))
        self.assertIn(builtin_name, xconfig.PLUGINS_DICT)


class TestPluginManageMeta(BaseTestCase):
    """插件管理页的查看meta功能"""

    PLUGIN_NAME = "unit_test_plugin_meta.py"

    PLUGIN_CODE = '''# -*- coding:utf-8 -*-
# @api-level 2.8
# @title 插件meta单元测试
# @description 仅用于测试查看meta
# @category test
# @category develop
from xnote.core.xtemplate import BasePlugin

class Main(BasePlugin):
    def render(self):
        return "unit-test-plugin-meta"
'''

    def setUp(self):
        # 预热: 首个请求会触发插件目录的懒加载, 该过程会重建 PLUGINS_DICT,
        # 会冲掉刚手动注册的插件, 所以先消耗掉这次加载
        self.request_app("/plugin_manage")

        self.fpath = os.path.join(xconfig.PLUGINS_DIR, self.PLUGIN_NAME)
        xutils.savetofile(self.fpath, self.PLUGIN_CODE)
        load_plugin_file(self.fpath)

    def tearDown(self):
        xconfig.PLUGINS_DICT.pop(self.PLUGIN_NAME, None)
        if os.path.exists(self.fpath):
            os.remove(self.fpath)

    def request_meta(self):
        url = "/plugin_manage?action=meta&plugin_name=" + xutils.quote(self.PLUGIN_NAME)
        return self.json_request_return_dict(url)

    def test_meta_action_rendered_in_page(self):
        # 表格的「操作」列渲染出查看meta的链接
        body = self.request_app("/plugin_manage").data.decode("utf-8")
        self.assertIn(self.PLUGIN_NAME, body)
        self.assertRegex(body, r'class="[^"]*plugin-meta-btn[^"]*"')
        self.assertRegex(body, r'href="\?action=meta&(amp;)?plugin_name=unit_test_plugin_meta\.py"')

    def test_view_meta(self):
        data = self.request_meta()
        self.assertTrue(data.get("success"))
        self.assertEqual(self.PLUGIN_NAME, data.get("plugin_name"))
        self.assertEqual(self.fpath, data.get("fpath"))

        meta = data.get("meta")
        self.assertEqual("插件meta单元测试", meta.get("title"))
        self.assertEqual("2.8", meta.get("api-level"))
        # 写了多个 @category 时聚合为 list
        self.assertEqual(["test", "develop"], meta.get("category"))

    def test_view_meta_without_name(self):
        data = self.json_request_return_dict("/plugin_manage?action=meta")
        self.assertFalse(data.get("success"))
        self.assertIn("plugin_name", data.get("message"))

    def test_view_meta_not_exists(self):
        data = self.json_request_return_dict("/plugin_manage?action=meta&plugin_name=not_exists_plugin.py")
        self.assertFalse(data.get("success"))
        self.assertIn("不存在", data.get("message"))


class TestDeletePluginByFileApi(BaseTestCase):
    """通过文件接口删除插件文件(比如 code/edit 页面的删除按钮), 内存中的插件同步失效"""

    PLUGIN_NAME = "unit_test_plugin_fs_delete.py"

    PLUGIN_CODE = '''# -*- coding:utf-8 -*-
# @api-level 2.8
# @title 文件接口删除插件测试
# @description 仅用于测试删除插件文件
# @category test
from xnote.core.xtemplate import BasePlugin

class Main(BasePlugin):
    def render(self):
        return "unit-test-plugin-fs-delete"
'''

    def setUp(self):
        # 删除是软删除(移动到回收站), 把回收站重定向到临时目录, 避免写脏 testdata/trash
        self._trash = fsutil.FileUtilConfig.trash_dir
        self.tmp = tempfile.TemporaryDirectory()
        fsutil.FileUtilConfig.trash_dir = os.path.join(self.tmp.name, "trash")
        os.makedirs(fsutil.FileUtilConfig.trash_dir)

        self.fpath = os.path.join(xconfig.PLUGINS_DIR, self.PLUGIN_NAME)
        xutils.savetofile(self.fpath, self.PLUGIN_CODE)
        load_plugin_file(self.fpath)

    def tearDown(self):
        xconfig.PLUGINS_DICT.pop(self.PLUGIN_NAME, None)
        if os.path.exists(self.fpath):
            os.remove(self.fpath)
        fsutil.FileUtilConfig.trash_dir = self._trash
        self.tmp.cleanup()

    def test_delete_plugin_file(self):
        self.assertIn(self.PLUGIN_NAME, xconfig.PLUGINS_DICT)

        resp = json_request_return_dict("/fs_api/remove", method="POST", data=dict(path=self.fpath))
        self.assertEqual("success", resp["code"])

        self.assertFalse(os.path.exists(self.fpath))
        # 内存中的插件同步移除, 插件地址立即失效
        self.assertNotIn(self.PLUGIN_NAME, xconfig.PLUGINS_DICT)
        body = self.request_app("/plugin/" + self.PLUGIN_NAME).data.decode("utf-8")
        self.assertIn("不存在", body)

    def test_delete_common_file_keeps_plugins(self):
        # 删除普通文件不应该影响插件的注册状态
        plugin_names = list(xconfig.PLUGINS_DICT.keys())
        path = os.path.join(xconfig.PLUGINS_DIR, "unit_test_common_file.txt")
        xutils.savetofile(path, "not a plugin")

        try:
            resp = json_request_return_dict("/fs_api/remove", method="POST", data=dict(path=path))
            self.assertEqual("success", resp["code"])
            self.assertEqual(plugin_names, list(xconfig.PLUGINS_DICT.keys()))
        finally:
            if os.path.exists(path):
                os.remove(path)

