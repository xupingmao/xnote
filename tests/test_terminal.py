# -*- coding:utf-8 -*-
"""Web终端(xterm.js + /api/v1/tools/terminal)的接口测试

只验证数据与逻辑: 会话创建、输入输出、会话终止、异常参数
"""

import base64
import time

from . import test_base
from .test_base import json_request_return_dict

API_PREFIX = "/api/v1/tools/terminal"

def b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")

def poll_until(session_id: str, keyword: str, timeout: float = 10.0) -> str:
    """轮询直到输出中出现关键词，返回累计输出"""
    deadline = time.time() + timeout
    output = ""
    while time.time() < deadline:
        resp = json_request_return_dict(API_PREFIX + "/poll", method="POST",
                                        data=dict(session_id=session_id, wait_ms=500))
        assert resp.get_bool("success"), resp.get_str("message")
        output += resp.get_dict("data").get_str("output")
        if keyword in output:
            return output
    raise AssertionError(f"等待输出超时, 期待关键词({keyword}), 实际输出: {output!r}")

class TerminalApiTest(test_base.BaseTestCase):
    """终端会话API测试"""

    def kill_session(self, session_id):
        return json_request_return_dict(API_PREFIX + "/kill", method="POST",
                                        data=dict(session_id=session_id))

    def start_session(self, shell: str = ""):
        return json_request_return_dict(API_PREFIX + "/start", method="POST",
                                        data=dict(shell=shell, cols=80, rows=24))

    def test_start_poll_write_kill(self):
        # 1. 创建会话
        resp = self.start_session()
        self.assertTrue(resp.get_bool("success"), resp.get_str("message"))
        session_id = resp.get_dict("data").get_str("session_id")
        self.assertTrue(len(session_id) > 0)
        self.assertIn(resp.get_dict("data").get_str("mode"), ("conpty", "pty", "pipe"))
        self.assertTrue(resp.get_dict("data").get_bool("running"))

        try:
            # 2. 执行命令并读取输出
            write_resp = json_request_return_dict(API_PREFIX + "/write", method="POST",
                                                  data=dict(session_id=session_id,
                                                            input=b64("echo xnote_terminal_test\r")))
            self.assertTrue(write_resp.get_bool("success"), write_resp.get_str("message"))
            output = poll_until(session_id, "xnote_terminal_test")
            self.assertTrue(len(output) > 0)

            # 3. 中文输入输出
            write_resp = json_request_return_dict(API_PREFIX + "/write", method="POST",
                                                  data=dict(session_id=session_id,
                                                            input=b64("echo 你好\r")))
            self.assertTrue(write_resp.get_bool("success"), write_resp.get_str("message"))
            poll_until(session_id, "你好")
        finally:
            # 4. 终止会话
            kill_resp = self.kill_session(session_id)
            self.assertTrue(kill_resp.get_bool("success"))

        # 5. 会话删除后再轮询应失败
        poll_resp = json_request_return_dict(API_PREFIX + "/poll", method="POST",
                                             data=dict(session_id=session_id, wait_ms=0))
        self.assertFalse(poll_resp.get_bool("success"))

    def test_start_with_invalid_cwd(self):
        resp = json_request_return_dict(API_PREFIX + "/start", method="POST",
                                        data=dict(cwd="/path/not/exists"))
        self.assertFalse(resp.get_bool("success"))

    def test_write_with_bad_base64(self):
        resp = self.start_session()
        self.assertTrue(resp.get_bool("success"), resp.get_str("message"))
        session_id = resp.get_dict("data").get_str("session_id")
        try:
            write_resp = json_request_return_dict(API_PREFIX + "/write", method="POST",
                                                  data=dict(session_id=session_id,
                                                            input="!!!not-base64!!!"))
            self.assertFalse(write_resp.get_bool("success"))
        finally:
            self.kill_session(session_id)

    def test_write_with_invalid_session(self):
        write_resp = json_request_return_dict(API_PREFIX + "/write", method="POST",
                                              data=dict(session_id="not-exists",
                                                        input=b64("echo hello\r")))
        self.assertFalse(write_resp.get_bool("success"))

    def test_kill_is_idempotent(self):
        kill_resp = json_request_return_dict(API_PREFIX + "/kill", method="POST",
                                             data=dict(session_id="not-exists"))
        self.assertTrue(kill_resp.get_bool("success"))

    def test_unknown_action(self):
        resp = json_request_return_dict(API_PREFIX + "/unknown_action", method="POST", data=dict())
        self.assertFalse(resp.get_bool("success"))

    def test_page_render(self):
        # 页面由 LoadInnerToolHandler 渲染，验证不报错即可
        self.check_200("/tools/terminal")

    def test_session_manager(self):
        from xnote_handlers.tools.terminal import get_session_manager
        manager = get_session_manager()
        resp = self.start_session()
        self.assertTrue(resp.get_bool("success"), resp.get_str("message"))
        session_id = resp.get_dict("data").get_str("session_id")
        try:
            session = manager.get_session(session_id)
            self.assertIsNotNone(session)
            self.assertEqual(session_id, session.id)
        finally:
            self.kill_session(session_id)
        self.assertIsNone(manager.get_session(session_id))

        # 会话数量统计
        self.assertEqual(0, manager.get_count())
