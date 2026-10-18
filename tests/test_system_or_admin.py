# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-10-14 09:30:29
@LastEditors  : xupingmao
@LastEditTime : 2024-03-31 14:37:13
@FilePath     : /xnote/tests/test_admin.py
@Description  : 描述
"""

import web.utils

from . import test_base
from xnote.core import xconfig, xmanager, xauth
from xnote.service import JobService
from xnote.service.system_meta_service import SystemMetaEnum
from .test_base import json_request_return_dict
from xutils.sqldb.utils import get_sqlite_table_struct
from xnote_handlers.admin.repair_admin import RepairHandler
from xnote.core.test_env import TestEnv

app = test_base.init()

class TestMain(test_base.BaseTestCase):
    """测试管理后台的功能"""
    
    def test_db_struct(self):
        self.check_OK("/system/db/struct?table_name=user")
        
        
    def assert_no_auth(self, response, pattern: str):
        if response.status == "401 Unauthorized":
            return
        
        if "Location" not in response.headers:
            raise Exception(f"发现权限拦截漏洞, pattern={pattern}")
        
        if "/unauthorized" in response.headers['Location']:
            return
        raise Exception(f"发现权限拦截漏洞, pattern={pattern}")

    def test_admin_auth(self):
        print("")
        
        skip_list = set([
            "/system/settings",
            "/system/stats",
            "/system/stats/location",
            "/system/index",
            "/system/sys",
            "/system/system",
            r"/system/user\.css",
            r"/system/user\.js",
            "/system/log/visit",
            "/system/todo",
            "/system/develop",
        ])

        check_list = set([
            "/plugins_upload",
            "/plugins_new",
            "/plugins_new/command",
        ])

        try:
            # 登录普通用户
            xauth.TestEnv.login_user("test")

            mapping = xmanager.get_handler_manager().mapping
            
            for pattern, raw_handler in web.utils.group(mapping, 2):
                if pattern in skip_list:
                    continue
                if pattern.startswith("/system/") or pattern in check_list or pattern.startswith("/admin/"):
                    print(f"Check {pattern} ...")
                    handler = raw_handler.handler_class

                    if hasattr(handler, "GET"):
                        response = self.request_app(pattern, method="GET")
                        self.assert_no_auth(response, pattern)
                    
                    if hasattr(handler, "POST"):
                        response = self.request_app(pattern, method="POST")
                        self.assert_no_auth(response, pattern)
        finally:
            xauth.TestEnv.login_user("admin")
        
    def test_admin_functions(self):
        self.check_OK("/admin/functions")

    def test_admin_job(self):
        self.check_OK("/admin/test_job")
        self.check_OK("/admin/jobs")
        
        job_list, amount = JobService.list_job_page()
        assert len(job_list) > 0
        assert amount > 0
        
        job_id = job_list[0].id
        
        self.check_OK(f"/admin/jobs?action=view&job_id={job_id}")
        self.check_OK(f"/admin/jobs?action=edit&job_id={job_id}")
        self.check_OK(f"/admin/jobs?action=delete&job_id={job_id}")
        
    def test_example(self):
        self.check_OK("/examples/table")
        self.check_OK("/examples/text")
        self.check_OK("/examples/tab")
        self.check_OK("/examples/dialog")
        self.check_OK("/examples/list_view")
        self.check_OK("/examples/calendar")
        self.check_OK("/examples/list_plugin")
    
    def test_admin_test(self):
        self.check_OK("/admin/test?type=lock")


    def test_thread_info(self):
        self.check_OK("/system/thread_info")

    def test_admin_repair(self):
        self.check_OK("/admin/repair")
        self.check_OK("/admin/repair?action=repair&code=fix_msg_tag")

    def test_system_template_cache(self):
        self.check_OK("/system/template_cache")

    def test_system_log(self):
        self.check_OK("/system/clipboard-monitor?log_type=clip")

    def test_system_config_update(self):
        data = dict(key = SystemMetaEnum.dev_mode.meta_key, value = "1")
        result = json_request_return_dict("/system/config", method="POST", data=data)
        assert result["success"] == True

        data = dict(key = "config.sys.no_such_key", value = "1")
        result = json_request_return_dict("/system/config", method="POST", data=data)
        assert result["success"] == False

    def test_admin_settings_switch_render(self):
        # 管理员设置页：布尔开关应用 ListViewSwitch 组件渲染，并直连 /system/config 持久化
        # （验证行为/数据正确性，不验证 CSS 样式或 DOM 结构）
        resp = self.request_app("/system/settings?category=admin")
        self.assertIn(resp.status, ("200 OK", "303 See Other", "302 Found"))
        body = resp.data
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        meta = SystemMetaEnum.sqlite_mem_sample_enabled
        # 开关行渲染出对应的配置项 key（内容正确性）
        assert meta.meta_key in body
        # 开关通过 oninput_ajax_url 直连持久化接口（行为正确性）
        assert "data-oninput-ajax-url" in body
        assert ("/system/config?key=" + meta.meta_key) in body
        # URL 只应被 HTML 转义一次（& -> &amp;），不能双重转义（&amp;amp; 会破坏 &type/&p 参数）
        assert "&amp;amp;" not in body

    def test_sqlite_mem_switch_persist(self):
        # 开关回调 /system/config 后，SQLite 内存采样开关应即时生效（无需重启）
        from xutils import _sqlite_mem
        meta = SystemMetaEnum.sqlite_mem_sample_enabled
        try:
            result = json_request_return_dict("/system/config", method="POST",
                                              data=dict(key=meta.meta_key, value="0", type="int", p="sys"))
            assert result["success"] == True
            assert _sqlite_mem.is_enabled() == False

            result = json_request_return_dict("/system/config", method="POST",
                                              data=dict(key=meta.meta_key, value="1", type="int", p="sys"))
            assert result["success"] == True
            assert _sqlite_mem.is_enabled() == True
        finally:
            _sqlite_mem.set_enabled(True)

    def test_user_settings_switch_render(self):
        # 搜索设置 / 笔记设置 页的用户级布尔开关也应使用 add_switch 直连 /system/config?p=user
        # （验证行为/数据正确性，不验证 CSS 样式或 DOM 结构）
        from xnote.core.xnote_user_config import UserConfig
        # 每个设置页只渲染自己的一组用户级布尔开关
        category_keys = {
            "search": (UserConfig.search_message_detail_show.key,
                       UserConfig.search_plugin_detail_show.key),
            "": (UserConfig.show_md_preview.key,
                 UserConfig.show_comment_edit.key),
        }
        for category, user_keys in category_keys.items():
            resp = self.request_app("/system/settings?category=" + category)
            self.assertIn(resp.status, ("200 OK", "303 See Other", "302 Found"))
            body = resp.data
            if isinstance(body, bytes):
                body = body.decode("utf-8")
            assert "data-oninput-ajax-url" in body
            # 开关回调走用户配置持久化路径
            assert "p=user" in body
            # 该页相关配置项的 key 应出现在页面（内容正确性）
            for key in user_keys:
                assert key in body

    def test_user_switch_persist(self):
        # 用户级开关回调 /system/config?p=user 后，配置应持久化
        from xnote.core import xauth
        from xnote.core.xnote_user_config import UserConfig
        config = UserConfig.search_message_detail_show
        user_id = xauth.current_user_id()
        try:
            result = json_request_return_dict("/system/config", method="POST",
                                              data=dict(key=config.key, value="1", type="str", p="user"))
            assert result["success"] == True
            assert config.get_str(user_id) == "1"

            result = json_request_return_dict("/system/config", method="POST",
                                              data=dict(key=config.key, value="0", type="str", p="user"))
            assert result["success"] == True
            assert config.get_str(user_id) == "0"
        finally:
            config.save_config(user_id=user_id, value=config.default_value)

    def test_backup(self):
        TestEnv.is_test = True
        TestEnv.skip_backup = False
        
        resp = self.json_request_return_dict("/system/backup")
        assert resp["success"] == True

        db_path = SystemMetaEnum.db_backup_file.meta_value
        table_struct = get_sqlite_table_struct(db_path, "kv_store")
        print("table_struct:", table_struct.columns)
        pk = table_struct.pk_column
        assert pk != None
        assert pk.type == "varbinary(100)"
        assert pk.name == "key"

    def test_repair_tools(self):
        for tool in RepairHandler.repair_rows:
            tool.do_repair()


    def test_tools_shell(self):
        self.check_OK("/tools/shell")

    def test_handler_profile(self):
        self.check_OK("/system/handler_profile")

    def test_trace_malloc_sqlite_tab(self):
        # 内存分析 - SQLite 内存 tab
        self.check_OK("/system/trace_malloc?tab=sqlite")
        # 内存分析 - 默认内存快照 tab
        self.check_OK("/system/trace_malloc")
