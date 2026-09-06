# -*- coding: utf-8 -*-
# @author xupingmao
# @since 2026/09/05
"""xnote-cli 自动化测试

覆盖：
- CLI 核心：命令注册、分发、会话存储、插件命令转发
- 服务端接口：note search/view/save/delete、cli login/command_list/run/backup
"""
import os
import sys
import json
import tempfile
import uuid

from tests import test_base
from tests.test_base import BaseTestCase

import xnote_cli
from xnote_cli import XnoteCliContext


def create_test_note(content, note_type="md"):
    """在测试环境创建一个笔记，返回 note_id（使用唯一名称避免冲突）"""
    from xnote_handlers.note import dao
    from xnote_handlers.note.models import NoteDO
    name = "cli测试笔记_%s" % uuid.uuid4().hex[:8]
    note = NoteDO()
    note.creator = "admin"
    note.creator_id = 1
    note.name = name
    note.content = content
    note.type = note_type
    note.level = 1
    note.tags = []
    return dao.create_note(note)


class CliCoreTestCase(BaseTestCase):
    """CLI 核心逻辑测试（不依赖真实服务端）"""

    def test_register_and_list(self):
        called = {}

        def handler(ctx):
            called["ok"] = True
            return 0

        xnote_cli.register_cmd("__core_test", handler, "test help")
        self.assertIsNotNone(xnote_cli.get_command("__core_test"))
        names = [c.name for c in xnote_cli.list_commands()]
        self.assertIn("__core_test", names)

    def test_match_local_command(self):
        # 本地命令（客户端定义）按扁平名称匹配
        name, args = xnote_cli._match_command(["version"])
        self.assertEqual(name, "version")
        self.assertEqual(args, [])

    def test_remote_command_not_matched_locally(self):
        # note-view 等是服务端远程命令，不在客户端本地命令表中（测试进程里
        # 服务端插件会被 xconfig.init 一并导入而污染 COMMANDS，这里隔离成本地表）
        import unittest.mock as mock
        local_cmds = {}
        with mock.patch.object(xnote_cli, "COMMANDS", local_cmds):
            xnote_cli._registered = False
            xnote_cli._ensure_registered()
            name, args = xnote_cli._match_command(["note-view", "123"])
            self.assertEqual(name, "")
            self.assertEqual(args, ["note-view", "123"])

    def test_main_dispatch_builtin(self):
        called = {}

        def handler(ctx):
            called["args"] = ctx.args
            return 0

        xnote_cli.register_cmd("__dispatch", handler)
        code = xnote_cli.main(["__dispatch", "a", "b"])
        self.assertEqual(code, 0)
        self.assertEqual(called["args"], ["a", "b"])

    def test_session_roundtrip(self):
        import unittest.mock as mock
        from xnote_cli.session import SessionInfo
        tmp = os.path.join(tempfile.mkdtemp(), "session.json")
        with mock.patch.object(xnote_cli.session, "get_session_path", lambda: tmp):
            xnote_cli.save_session(SessionInfo(username="admin", cookie="sid_list=x"))
            loaded = xnote_cli.load_session()
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.username, "admin")
            self.assertEqual(loaded.cookie, "sid_list=x")

    def test_parse_html_response_as_unauthorized(self):
        # 未登录时服务端会返回 HTML 登录页，应当转换为明确的未登录提示
        resp = xnote_cli._parse_response(200, {"Content-Type": "text/html"},
                                         b"<!DOCTYPE html><html>...</html>")
        self.assertFalse(resp.success)
        self.assertEqual(resp.code, "unauthorized")
        self.assertIn("login", resp.message)

    def test_extract_session_cookie(self):
        self.assertEqual(
            xnote_cli._extract_session_cookie("sid_list=abc,def; Path=/"),
            "sid_list=abc,def")
        # 登录会同时下发 sid 与 sid_list 两个 Set-Cookie，二者都要提取，
        # 且 sid 才是服务端鉴权使用的 cookie
        self.assertEqual(
            xnote_cli._extract_session_cookie(
                "sid=xyz; Path=/, sid_list=abc,def; Path=/"),
            "sid=xyz; sid_list=abc,def")
        self.assertIsNone(xnote_cli._extract_session_cookie(""))

    def test_note_search_plugin_handler(self):
        # note-search 已变成服务端插件命令，直接测试其 handler 逻辑
        from xnote_handlers.cli.plugins import note_plugin
        import unittest.mock as mock

        fake_note = mock.MagicMock()
        fake_note.creator_id = 1
        fake_note.is_public = 0
        fake_note.note_id = 1
        fake_note.name = "demo"
        fake_note.is_group = False
        fake_note.id = 1
        fake_note.type = "md"
        fake_note.url = "/note/view/1"

        with mock.patch.object(note_plugin.dao, "search_name", return_value=[fake_note]), \
             mock.patch.object(note_plugin.dao, "search_content", return_value=[]), \
             mock.patch.object(note_plugin.xauth, "current_user_id", return_value=1), \
             mock.patch.object(note_plugin.xauth, "current_name_str", return_value="admin"):
            ctx = XnoteCliContext(command="note-search", args=["hello"])
            result = note_plugin.note_search_handler(ctx)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["id"], 1)

    def test_note_edit_plugin_handler(self):
        from xnote_handlers.cli.plugins import note_plugin
        import unittest.mock as mock

        old = mock.MagicMock()
        old.creator_id = 1
        old.version = 1
        old.get_url.return_value = "/note/view/9"

        with mock.patch.object(note_plugin.dao, "get_by_id", return_value=old), \
             mock.patch.object(note_plugin.xauth, "current_user_id", return_value=1), \
             mock.patch.object(note_plugin, "update_and_notify") as m_update:
            ctx = XnoteCliContext(command="note-edit", args=["9", "new content"])
            out = note_plugin.note_edit_handler(ctx)
            self.assertIn("已更新", out)
            m_update.assert_called_once()

    def test_note_list_plugin_handler(self):
        from xnote_handlers.cli.plugins import note_plugin
        import unittest.mock as mock

        group_item = mock.MagicMock()
        group_item.note_id = 1
        group_item.name = "我的笔记本"
        group_item.type = "group"
        group_item.parent_id = 0
        group_item.url = "/note/group/1"

        note_item = mock.MagicMock()
        note_item.note_id = 2
        note_item.name = "一篇笔记"
        note_item.type = "md"
        note_item.parent_id = 1
        note_item.url = "/note/view/2"

        def fake_list_by_parent(creator, parent_id=0, **kw):
            # 模拟某个父目录下同时含有子笔记本(group)和笔记(note)
            return [group_item, note_item]

        with mock.patch.object(note_plugin.dao, "list_by_parent",
                               side_effect=fake_list_by_parent), \
             mock.patch.object(note_plugin.xauth, "current_name_str",
                               return_value="admin"):
            # 根目录（无参数）：等价于 /note/group，只列笔记本（group）
            ctx_root = XnoteCliContext(command="note-list", args=[])
            root_result = note_plugin.note_list_handler(ctx_root)
            self.assertEqual(len(root_result), 1)
            self.assertEqual(root_result[0]["type"], "group")
            self.assertEqual(root_result[0]["id"], 1)

            # 指定父文档 id：列出全部子项（笔记 + 子笔记本）
            ctx_sub = XnoteCliContext(command="note-list", args=["1"])
            sub_result = note_plugin.note_list_handler(ctx_sub)
            self.assertEqual(len(sub_result), 2)
            self.assertEqual({item["id"] for item in sub_result}, {1, 2})

            # 参数需为数字
            with self.assertRaises(xnote_cli.XnoteCliError):
                note_plugin.note_list_handler(
                    XnoteCliContext(command="note-list", args=["abc"]))

    def test_remote_command_dispatch(self):
        # 本地未命中时，应把远程命令转发到 /api/cli/run
        import unittest.mock as mock
        from xnote_cli.session import SessionInfo

        forwarded = {}

        def fake_load_remote(ctx):
            return {"note-view": "查看笔记内容"}

        def fake_forward(ctx, name, args, use_json=False):
            forwarded["name"] = name
            forwarded["args"] = args
            forwarded["use_json"] = use_json
            return 0

        local_cmds = {}
        with mock.patch.object(xnote_cli, "COMMANDS", local_cmds), \
             mock.patch.object(xnote_cli, "load_session",
                               return_value=SessionInfo(commands={"note-view": "查看笔记内容"})), \
             mock.patch.object(xnote_cli, "_load_remote_commands", fake_load_remote), \
             mock.patch.object(xnote_cli, "_forward_to_server", fake_forward):
            xnote_cli._registered = False
            xnote_cli._ensure_registered()
            code = xnote_cli.main(["note-view", "123"])
            self.assertEqual(code, 0)
            self.assertEqual(forwarded["name"], "note-view")
            self.assertEqual(forwarded["args"], ["123"])

    def test_login_caches_remote_commands(self):
        # 登录成功后应把服务端远程命令列表缓存进会话
        import unittest.mock as mock
        import email.message

        msg = email.message.Message()
        msg["Set-Cookie"] = "sid=SECRET; Path=/"
        msg["Set-Cookie"] = "sid_list=SECRET; Path=/"

        class FakeResp:
            def __init__(self):
                self.headers = msg
            def read(self):
                return b'{"success": true, "data": {"name": "admin"}}'

        saved = {}

        with mock.patch("urllib.request.urlopen", return_value=FakeResp()), \
             mock.patch("xnote_cli.commands.input", return_value="admin"), \
             mock.patch("xnote_cli.commands.get_password", return_value="admin"), \
             mock.patch("xnote_cli.commands.save_session") as sp, \
             mock.patch.object(xnote_cli.commands, "_get_server_commands",
                              return_value={"note-view": "查看笔记内容"}):
            rc = xnote_cli.commands.do_login(xnote_cli.XnoteCliContext())
            self.assertEqual(rc, 0)
            saved = sp.call_args_list[-1][0][0]
            self.assertEqual(saved.cookie, "sid=SECRET; sid_list=SECRET")
            self.assertEqual(saved.commands, {"note-view": "查看笔记内容"})

    def test_session_command_no_login(self):
        # session 命令直接输出 JSON；未登录时 logged_in 为 false
        import io
        import contextlib
        import unittest.mock as mock
        with mock.patch.object(xnote_cli.commands, "load_session", return_value=None):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = xnote_cli.commands.do_session(XnoteCliContext())
        self.assertEqual(rc, 0)
        out = json.loads(buf.getvalue())
        self.assertFalse(out["logged_in"])

    def test_session_command_with_login(self):
        # 已登录时输出完整会话信息 JSON
        import io
        import contextlib
        import unittest.mock as mock
        from xnote_cli.session import SessionInfo
        session = SessionInfo(username="admin", server_url="http://x",
                             cookie="sid=x", commands={"note-view": "查看"})
        with mock.patch.object(xnote_cli.commands, "load_session", return_value=session):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = xnote_cli.commands.do_session(XnoteCliContext())
        self.assertEqual(rc, 0)
        out = json.loads(buf.getvalue())
        self.assertTrue(out["logged_in"])
        self.assertEqual(out["username"], "admin")
        self.assertEqual(out["server_url"], "http://x")
        self.assertEqual(out["commands"], {"note-view": "查看"})

    def test_refresh_requires_login(self):
        # 未登录时 refresh 直接报错退出
        import unittest.mock as mock
        with mock.patch.object(xnote_cli.commands, "load_session", return_value=None):
            rc = xnote_cli.commands.do_refresh(XnoteCliContext())
        self.assertEqual(rc, 1)

    def test_refresh_updates_session_cache(self):
        # 已登录时重新拉取远程命令并更新会话缓存
        import unittest.mock as mock
        from xnote_cli.session import SessionInfo
        session = SessionInfo(username="admin", server_url="http://x", cookie="sid=x")
        with mock.patch.object(xnote_cli.commands, "load_session", return_value=session), \
             mock.patch.object(xnote_cli.commands, "_get_server_commands",
                              return_value={"note-view": "查看", "backup": "备份"}), \
             mock.patch.object(xnote_cli.commands, "save_session") as sp:
            rc = xnote_cli.commands.do_refresh(XnoteCliContext())
        self.assertEqual(rc, 0)
        self.assertEqual(session.commands, {"note-view": "查看", "backup": "备份"})
        sp.assert_called_once_with(session)

    def test_render_table(self):
        # _render_table 把列表数据渲染为带表头的文本表格
        rows = [{"id": 1, "name": "笔记本", "type": "group", "url": "/note/group/1"}]
        out = xnote_cli._render_table(rows)
        self.assertIsInstance(out, str)
        self.assertIn("name", out)
        self.assertIn("笔记本", out)
        self.assertIn("id", out)

    def test_render_table_empty(self):
        self.assertEqual(xnote_cli._render_table([]), "(无数据)")

    def test_display_width_counts_cjk_as_two(self):
        # 中文等宽字符在终端占 2 个单元格，英文字符占 1 个
        self.assertEqual(xnote_cli._display_width("ab"), 2)
        self.assertEqual(xnote_cli._display_width("中文"), 4)
        self.assertEqual(xnote_cli._display_width("a中b文"), 6)

    def test_render_table_cjk_alignment(self):
        # 中英文混排时，各列按显示宽度对齐（中文占 2 格），各行总宽度应一致
        rows = [
            {"id": 1, "name": "笔记本", "type": "group"},
            {"id": 22, "name": "hello world", "type": "md"},
        ]
        out = xnote_cli._render_table(rows)
        lines = out.split("\n")
        # 两条数据行按显示宽度对齐，因此总宽度相等
        self.assertEqual(xnote_cli._display_width(lines[2]),
                         xnote_cli._display_width(lines[3]))

    def test_forward_note_list_defaults_to_table(self):
        # 默认（无 --json）note-list/note-search 以表格形式输出
        import io
        import contextlib
        import unittest.mock as mock
        fake = xnote_cli.ApiResult(success=True, data=[
            {"id": 1, "name": "笔记本", "type": "group", "url": "/note/group/1"}])
        with mock.patch.object(xnote_cli, "request", return_value=fake), \
             contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = xnote_cli._forward_to_server(XnoteCliContext(), "note-list", [], use_json=False)
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("笔记本", out)
        # 表格输出不应是 JSON（没有键名引号包裹）
        self.assertNotIn('"id"', out)

    def test_forward_note_search_json_with_flag(self):
        # 设置 --json 时以 JSON 格式输出
        import io
        import contextlib
        import unittest.mock as mock
        fake = xnote_cli.ApiResult(success=True, data=[
            {"id": 1, "name": "笔记本", "type": "group", "url": "/note/group/1"}])
        with mock.patch.object(xnote_cli, "request", return_value=fake), \
             contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = xnote_cli._forward_to_server(XnoteCliContext(),
                                             "note-search", [], use_json=True)
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        # JSON 输出包含键名引号
        self.assertIn('"id"', out)

    def test_main_forwards_json_flag_for_remote_command(self):
        # main 解析 --json 后，应透传给 _forward_to_server（端到端校验 argparse 接线）
        import unittest.mock as mock
        from xnote_cli.session import SessionInfo
        captured = {}
        def fake_forward(ctx, name, args, use_json=False):
            captured["name"] = name
            captured["use_json"] = use_json
            return 0
        with mock.patch.object(xnote_cli, "COMMANDS", {}), \
             mock.patch.object(xnote_cli, "load_session",
                              return_value=SessionInfo(username="admin",
                                                       commands={"note-search": "搜索"})), \
             mock.patch.object(xnote_cli, "_load_remote_commands",
                              return_value={"note-search": "搜索"}), \
             mock.patch.object(xnote_cli, "_forward_to_server", fake_forward):
            xnote_cli._registered = False
            xnote_cli._ensure_registered()
            rc = xnote_cli.main(["note-search", "关键词", "--json"])
        self.assertEqual(rc, 0)
        self.assertEqual(captured["name"], "note-search")
        self.assertTrue(captured["use_json"])


class CliApiTestCase(BaseTestCase):
    """服务端接口测试（依赖测试 APP）"""

    def test_login_api(self):
        # 测试环境创建独立用户，避免依赖内置 admin 密码
        from xnote.core import xauth
        user_name = "clitest_%s" % uuid.uuid4().hex[:8]
        xauth.create_user(user_name, "123456")

        resp = self.request_app("/api/cli/login", method="POST",
                               data=json.dumps(dict(username=user_name,
                                                    password="123456")))
        self.assertEqual(resp.status, "200 OK")
        body = json.loads(resp.data.decode("utf-8"))
        self.assertTrue(body.get("success"))

    def test_command_list_api(self):
        resp = self.json_request("/api/cli/command_list", method="GET")
        self.assertTrue(resp["success"])
        names = [item["name"] for item in resp["data"]]
        # 内置示例插件命令
        self.assertIn("hello", names)
        # 服务端插件提供的远程命令（note/ops 插件）
        for cmd in ("note-view", "note-search", "note-edit", "note-delete",
                   "backup", "repair", "sync"):
            self.assertIn(cmd, names)

    def test_run_plugin_api(self):
        resp = self.json_request("/api/cli/run", method="POST",
                                 data=dict(cmd="hello", args="world"))
        self.assertTrue(resp["success"])
        self.assertEqual(resp["data"], "hello world")

    def test_run_unknown_command(self):
        resp = self.json_request("/api/cli/run", method="POST",
                                 data=dict(cmd="not_exist_cmd", args=""))
        self.assertFalse(resp["success"])

    def test_note_save_view_search_delete(self):
        note_id = create_test_note("cli search content")

        # view
        view_resp = self.json_request("/api/note/content?id=%s" % note_id,
                                      method="GET")
        self.assertTrue(view_resp["success"])
        self.assertEqual(view_resp["data"], "cli search content")

        # search
        search_resp = self.json_request("/api/note/search?key=cli%20search",
                                        method="GET")
        self.assertTrue(search_resp["success"])
        ids = [item["id"] for item in search_resp["data"]]
        self.assertIn(note_id, ids)

        # save (update content)
        save_resp = self.json_request("/api/note/save", method="POST",
                                      data=dict(id=note_id, content="updated content"))
        self.assertTrue(save_resp["success"])

        view_resp2 = self.json_request("/api/note/content?id=%s" % note_id,
                                       method="GET")
        self.assertEqual(view_resp2["data"], "updated content")

        # delete
        del_resp = self.json_request("/api/note/delete", method="POST",
                                     data=dict(id=note_id))
        self.assertTrue(del_resp["success"])

    def test_backup_api(self):
        # 备份在测试环境可能未开启，这里只校验返回结构
        resp = self.json_request("/api/cli/backup", method="POST")
        self.assertIsInstance(resp, dict)
        self.assertIn("success", resp)

    def test_login_set_cookie_then_run_remote_command(self):
        # 全链路：登录下发会话 cookie -> 客户端提取 -> 用该 cookie 执行远程命令
        from xnote.core import xauth
        user_name = "clitest_%s" % uuid.uuid4().hex[:8]
        xauth.create_user(user_name, "123456")

        login_resp = self.request_app("/api/cli/login", method="POST",
                                     data=json.dumps(dict(username=user_name,
                                                          password="123456")))
        self.assertEqual(login_resp.status, "200 OK")
        login_body = json.loads(login_resp.data.decode("utf-8"))
        self.assertTrue(login_body.get("success"))

        # 测试环境不下发 Set-Cookie，登录接口通过响应体回传 sid，
        # 客户端据此构造会话 Cookie（与 do_login 逻辑一致）
        sid = (login_body.get("data") or {}).get("sid")
        self.assertTrue(sid, "登录成功后会话 sid 不应为空")
        cookie = "sid=%s" % sid

        # 携带登录 cookie 调用远程命令 note-search
        search_resp = self.request_app("/api/cli/run", method="POST",
                                      data=dict(cmd="note-search", args="x"),
                                      headers={"Cookie": cookie})
        self.assertEqual(search_resp.status, "200 OK")
        body = json.loads(search_resp.data.decode("utf-8"))
        # 鉴权通过 + 远程命令在服务端执行成功
        self.assertTrue(body.get("success"))
        self.assertIsInstance(body.get("data"), list)


if __name__ == "__main__":
    import unittest
    unittest.main()
