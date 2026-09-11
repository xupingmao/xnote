# -*- coding:utf-8 -*-
"""聊天机器人的测试用例"""

from .test_base import json_request_return_dict, request_html, BaseTestCase
from .test_base import init as init_app
from xnote.core import xauth, xtemplate
from xnote_handlers.chatbot import dao, reply_engine
from xnote_handlers.chatbot.chat_service import ChatService
from xnote_handlers.chatbot.chatbot_service import ChatBotService
from xnote_handlers.chatbot.models import (
    ChatMessageRecord,
    ChatSessionRecord,
    ChatType,
    SenderType,
)

app = init_app()


class ChatDaoTestCase(BaseTestCase):
    """Dao层的测试基类

    负责清理用例产生的数据。直接跑 pytest 时(不像 run-test.py)不会清空 testdata,
    不清理的话第二次运行会因为上一次的残留数据而失败。
    """

    def setUp(self):
        self.session_list = []

    def tearDown(self):
        for session in self.session_list:
            dao.ChatMessageDao.delete_by_session(session.session_id)
            dao.ChatSessionDao.delete_by_id(session.session_id, session.user_id)

    def create_session(self, user_id: int, title: str = "",
                       chat_type: str = ChatType.bot) -> ChatSessionRecord:
        session = ChatService.create_session(user_id, chat_type, title)
        self.session_list.append(session)
        return session

    def clean_user(self, user_id: int) -> None:
        """清理该用户的历史数据, 保证断言不受跨次运行的残留影响"""
        for session in dao.ChatSessionDao.list_by_user(user_id, limit=1000):
            dao.ChatMessageDao.delete_by_session(session.session_id)
            dao.ChatSessionDao.delete_by_id(session.session_id, user_id)


class TestChatSessionDao(ChatDaoTestCase):

    def test_create_and_get(self):
        record = ChatService.create_session(1, ChatType.bot, "测试会话")
        assert record.session_id > 0

        found = dao.ChatSessionDao.get_by_id(record.session_id)
        assert found is not None
        assert found.title == "测试会话"
        assert found.chat_type == ChatType.bot
        assert found.user_id == 1

    def test_list_by_user_order_by_update_time_desc(self):
        self.clean_user(2)
        first = self.create_session(2, "较早")
        second = self.create_session(2, "较晚")

        session_list = dao.ChatSessionDao.list_by_user(2)
        assert len(session_list) == 2
        # 按 update_time 倒序, 后建的排在前面
        assert session_list[0].session_id == second.session_id
        assert session_list[0].title == "较晚"
        assert session_list[1].session_id == first.session_id

    def test_list_by_user_filter_chat_type(self):
        self.clean_user(3)
        self.create_session(3, "机器人会话", ChatType.bot)
        self.create_session(3, "用户会话", ChatType.user)

        assert len(dao.ChatSessionDao.list_by_user(3, ChatType.bot)) == 1
        assert len(dao.ChatSessionDao.list_by_user(3, ChatType.user)) == 1
        assert len(dao.ChatSessionDao.list_by_user(3)) == 2

    def test_delete_by_id(self):
        record = self.create_session(4)
        assert dao.ChatSessionDao.delete_by_id(record.session_id, 4) == 1
        assert dao.ChatSessionDao.get_by_id(record.session_id) is None


class TestChatMessageDao(ChatDaoTestCase):

    def test_create_and_list(self):
        session_id = self.create_session(10).session_id
        for index in range(3):
            ChatService.send_message(session_id, SenderType.user, 10, "消息%d" % index)

        message_list = dao.ChatMessageDao.list_by_session(session_id)
        assert len(message_list) == 3
        # 按 message_id 正序
        assert message_list[0].content == "消息0"
        assert message_list[2].content == "消息2"
        assert message_list[0].sender_type == SenderType.user
        assert message_list[0].is_bot is False

    def test_list_recent_returns_asc(self):
        session_id = self.create_session(11).session_id
        for index in range(5):
            ChatService.send_message(session_id, SenderType.user, 11, "消息%d" % index)

        recent = dao.ChatMessageDao.list_recent(session_id, limit=2)
        assert len(recent) == 2
        # 取最近2条, 但仍然按时间正序返回
        assert recent[0].content == "消息3"
        assert recent[1].content == "消息4"

    def test_count_by_session(self):
        session_id = self.create_session(12).session_id
        assert dao.ChatMessageDao.count_by_session(session_id) == 0
        ChatService.send_message(session_id, SenderType.user, 12, "hello")
        ChatService.send_message(session_id, SenderType.bot, 0, "hi")
        assert dao.ChatMessageDao.count_by_session(session_id) == 2

    def test_delete_by_session(self):
        session_id = self.create_session(13).session_id
        ChatService.send_message(session_id, SenderType.user, 13, "hello")
        assert dao.ChatMessageDao.count_by_session(session_id) == 1

        dao.ChatMessageDao.delete_by_session(session_id)
        assert dao.ChatMessageDao.count_by_session(session_id) == 0


class TestDaoLimit(ChatDaoTestCase):
    """读取条数的限制, 防止外部传入过大的 limit"""

    def test_check_limit_normal(self):
        assert dao.check_limit(1) == 1
        assert dao.check_limit(20) == 20
        assert dao.check_limit(dao.MAX_LIMIT) == dao.MAX_LIMIT

    def test_check_limit_too_large(self):
        assert dao.check_limit(dao.MAX_LIMIT + 1) == dao.MAX_LIMIT
        assert dao.check_limit(99999999) == dao.MAX_LIMIT

    def test_check_limit_invalid(self):
        # 小于等于0视为未指定, 回退到默认值
        assert dao.check_limit(0) == dao.DEFAULT_LIMIT
        assert dao.check_limit(-1) == dao.DEFAULT_LIMIT

    def test_message_list_caps_limit(self):
        session_id = self.create_session(40).session_id
        message_list = dao.ChatMessageDao.list_by_session(session_id, limit=99999999)
        assert len(message_list) <= dao.MAX_LIMIT

    def test_message_list_zero_limit_not_raise(self):
        # limit=0 会被底层 assert 拦截, 应该在Dao层回退到默认值
        session_id = self.create_session(41).session_id
        ChatService.send_message(session_id, SenderType.user, 41, "hello")
        message_list = dao.ChatMessageDao.list_by_session(session_id, limit=0)
        assert len(message_list) == 1

    def test_session_list_caps_limit(self):
        self.create_session(42)
        session_list = dao.ChatSessionDao.list_by_user(42, limit=99999999)
        assert len(session_list) <= dao.MAX_LIMIT

    def test_session_list_zero_limit_uses_default(self):
        self.create_session(43)
        assert len(dao.ChatSessionDao.list_by_user(43, limit=0)) == 1

    def test_check_offset(self):
        assert dao.check_offset(0) == 0
        assert dao.check_offset(20) == 20
        # 负数会被底层 assert 拦截, 统一归零
        assert dao.check_offset(-1) == 0

    def test_negative_offset_not_raise(self):
        session_id = self.create_session(45).session_id
        ChatService.send_message(session_id, SenderType.user, 45, "hello")
        message_list = dao.ChatMessageDao.list_by_session(session_id, offset=-1)
        assert len(message_list) == 1

    def test_list_recent_caps_limit(self):
        session = self.create_session(44)
        session_id = session.session_id
        recent = dao.ChatMessageDao.list_recent(session_id, limit=99999999)
        assert len(recent) <= dao.MAX_LIMIT


class TestChatService(BaseTestCase):

    def test_send_message_updates_summary_and_title(self):
        session = ChatService.create_session(20, ChatType.bot)
        ChatService.send_message(session.session_id, SenderType.user, 20, "第一条消息")

        updated = dao.ChatSessionDao.get_by_id(session.session_id)
        assert updated is not None
        assert updated.last_message == "第一条消息"
        assert updated.title == "第一条消息"

    def test_title_not_overwritten(self):
        session = ChatService.create_session(21, ChatType.bot, "固定标题")
        ChatService.send_message(session.session_id, SenderType.user, 21, "内容")

        updated = dao.ChatSessionDao.get_by_id(session.session_id)
        assert updated is not None
        assert updated.title == "固定标题"
        assert updated.last_message == "内容"

    def test_get_session_check_owner(self):
        session = ChatService.create_session(22, ChatType.bot)
        assert ChatService.get_session(session.session_id, 22) is not None
        # 其他用户访问返回 None
        assert ChatService.get_session(session.session_id, 999) is None

    def test_get_or_create_session(self):
        first = ChatService.get_or_create_session(0, 23, ChatType.bot)
        assert first.session_id > 0

        # 传入已有会话时复用
        again = ChatService.get_or_create_session(first.session_id, 23, ChatType.bot)
        assert again.session_id == first.session_id

        # 传入无效ID时新建
        other = ChatService.get_or_create_session(999999, 23, ChatType.bot)
        assert other.session_id != first.session_id

    def test_delete_session_cascade_messages(self):
        session = ChatService.create_session(24, ChatType.bot)
        ChatService.send_message(session.session_id, SenderType.user, 24, "hello")

        assert ChatService.delete_session(session.session_id, 24) is True
        assert dao.ChatMessageDao.count_by_session(session.session_id) == 0
        assert dao.ChatSessionDao.get_by_id(session.session_id) is None

    def test_delete_session_of_other_user_fails(self):
        session = ChatService.create_session(25, ChatType.bot)
        assert ChatService.delete_session(session.session_id, 999) is False
        assert dao.ChatSessionDao.get_by_id(session.session_id) is not None


class TestReplyEngine(BaseTestCase):

    def reply(self, content: str, user_name: str = "admin"):
        ctx = reply_engine.build_context(user_name=user_name, content=content)
        return reply_engine.reply(ctx)

    def test_greeting_rule(self):
        result = self.reply("你好")
        assert result.rule_name == "greeting"
        assert "admin" in result.content

    def test_help_rule(self):
        assert self.reply("help").rule_name == "help"
        assert self.reply("帮助").rule_name == "help"
        assert self.reply("?").rule_name == "help"

    def test_time_rule(self):
        result = self.reply("时间")
        assert result.rule_name == "time"
        assert "现在是" in result.content

    def test_echo_rule(self):
        result = self.reply("复读 hello world")
        assert result.rule_name == "echo"
        assert result.content == "hello world"

    def test_echo_rule_keeps_case(self):
        result = self.reply("echo Hello World")
        assert result.rule_name == "echo"
        assert result.content == "Hello World"

    def test_whoami_rule(self):
        result = self.reply("我是谁")
        assert result.rule_name == "whoami"
        assert result.content == "你是 admin"

    def test_fallback(self):
        result = self.reply("zzz完全不认识的内容")
        assert result.rule_name == "fallback"
        assert "zzz完全不认识的内容" in result.content

    def test_prefix_rule_wins_over_contains(self):
        # "复读 hello" 同时命中 greeting 的 "hello" 与 echo 的前缀,
        # 前缀规则更具体, 应该优先
        assert self.reply("复读 hello").rule_name == "echo"

    def test_custom_rule_by_priority(self):
        rule = reply_engine.KeywordRule(
            name="custom",
            keywords=["自定义"],
            reply="自定义规则命中",
            priority=100,
        )
        reply_engine.register_rule(rule)
        try:
            assert self.reply("自定义内容").rule_name == "custom"
        finally:
            reply_engine.get_rules().remove(rule)


class TestChatBotService(BaseTestCase):

    def test_send_creates_session_and_reply(self):
        result = ChatBotService.send(30, "admin", 0, "你好")
        assert result.session is not None
        assert result.message is not None
        assert result.reply is not None

        assert result.session.chat_type == ChatType.bot
        assert result.message.sender_type == SenderType.user
        assert result.reply.sender_type == SenderType.bot
        assert result.reply.is_bot is True
        assert result.reply.content != ""

    def test_send_reuses_session(self):
        first = ChatBotService.send(31, "admin", 0, "hello")
        second = ChatBotService.send(31, "admin", first.session.session_id, "hello")

        assert second.session.session_id == first.session.session_id
        assert dao.ChatMessageDao.count_by_session(first.session.session_id) == 4

    def test_send_builds_commands_for_new_session(self):
        result = ChatBotService.send(32, "admin", 0, "你好")
        commands = result.commands
        assert isinstance(commands, list)
        assert len(commands) > 0

        types = [c["command"] for c in commands]
        # 新会话: 整体替换消息区 + 刷新隐藏会话ID + 刷新左侧列表
        assert "update_html" in types
        assert "update_value" in types

        # 消息区命令必须是整体替换(update_html), 顺带移除空提示
        message_cmds = [c for c in commands if c.get("id") == "message-list"]
        assert len(message_cmds) == 1
        assert message_cmds[0]["command"] == "update_html"
        assert "chat-message-row" in message_cmds[0]["value"]

        # 隐藏的会话ID被更新
        for c in commands:
            if c["command"] == "update_value":
                assert c["id"] == "current-session-id"
                assert c["value"] == result.session.session_id

        # 左侧会话列表被刷新
        assert any(c.get("id") == "session-list-inner" for c in commands)
        assert len(result.session_list) > 0

    def test_send_existing_session_appends(self):
        first = ChatBotService.send(33, "admin", 0, "你好")
        second = ChatBotService.send(33, "admin", first.session.session_id, "你好")

        message_cmds = [c for c in second.commands if c.get("id") == "message-list"]
        assert len(message_cmds) == 1
        assert message_cmds[0]["command"] == "append_html"
        assert "chat-message-row" in message_cmds[0]["value"]


class TestChatBotRender(BaseTestCase):

    def test_render_message_rows_escapes_content(self):
        from xnote_handlers.chatbot.chatbot_render import render_message_rows
        msg = ChatMessageRecord()
        msg.content = "hello <b>"
        msg.create_time = 0
        html = render_message_rows([msg])
        assert "chat-message-row" in html
        # 自动转义, 防止 XSS
        assert "hello &lt;b&gt;" in html

    def test_render_session_list_marks_active(self):
        from xnote_handlers.chatbot.chatbot_render import render_session_list
        session = ChatSessionRecord()
        session.session_id = 1
        session.title = "会话"
        session.last_message = "摘要"
        html = render_session_list([session], current_session_id=1)
        assert "chat-session-item" in html
        assert "active" in html


class TestChatBotApi(BaseTestCase):

    def test_send_api(self):
        resp = json_request_return_dict(
            "/api/chatbot/send", method="POST",
            data=dict(session_id=0, content="你好"))
        assert resp["success"] == True

        data = resp["data"]
        assert data["session"]["session_id"] > 0
        assert data["message"]["content"] == "你好"
        assert data["reply"]["sender_type"] == SenderType.bot
        assert len(data["reply"]["content"]) > 0

        # 后端下发的命令, 交给前端 xnote.executeCommands 执行
        assert "commands" in data
        assert len(data["commands"]) > 0
        assert any(c["command"] == "update_html" for c in data["commands"])
        assert any(c["id"] == "session-list-inner" for c in data["commands"])

    def test_send_empty_content(self):
        resp = json_request_return_dict(
            "/api/chatbot/send", method="POST",
            data=dict(session_id=0, content=""))
        assert resp["success"] == False
        assert resp["code"] == "400"

    def test_send_with_invalid_session(self):
        resp = json_request_return_dict(
            "/api/chatbot/send", method="POST",
            data=dict(session_id=999999, content="hello"))
        assert resp["success"] == False
        assert resp["code"] == "404"

    def test_message_list_api(self):
        send_resp = json_request_return_dict(
            "/api/chatbot/send", method="POST",
            data=dict(session_id=0, content="复读 测试内容"))
        session_id = send_resp["data"]["session"]["session_id"]

        resp = json_request_return_dict(
            "/api/chatbot/message/list?session_id=%s" % session_id)
        assert resp["success"] == True
        assert resp["data"]["total"] == 2

        contents = []
        for item in resp["data"]["messages"]:
            contents.append(item["content"])
        assert contents == ["复读 测试内容", "测试内容"]

    def test_message_list_invalid_session(self):
        resp = json_request_return_dict("/api/chatbot/message/list?session_id=999999")
        assert resp["success"] == False
        assert resp["code"] == "404"

    def test_session_list_api(self):
        json_request_return_dict(
            "/api/chatbot/session/create", method="POST",
            data=dict(title="会话列表测试"))

        resp = json_request_return_dict("/api/chatbot/session/list")
        assert resp["success"] == True
        assert resp["data"]["total"] > 0

        found = None
        for item in resp["data"]["sessions"]:
            if item["title"] == "会话列表测试":
                found = item
                break
        assert found is not None

    def test_session_create_and_delete(self):
        create_resp = json_request_return_dict(
            "/api/chatbot/session/create", method="POST",
            data=dict(title="待删除的会话"))
        assert create_resp["success"] == True
        session_id = create_resp["data"]["session_id"]

        delete_resp = json_request_return_dict(
            "/api/chatbot/session/delete", method="POST",
            data=dict(session_id=session_id))
        assert delete_resp["success"] == True
        assert dao.ChatSessionDao.get_by_id(session_id) is None

    def test_session_delete_invalid_id(self):
        resp = json_request_return_dict(
            "/api/chatbot/session/delete", method="POST",
            data=dict(session_id=0))
        assert resp["success"] == False
        assert resp["code"] == "400"


class TestChatBotPage(BaseTestCase):

    def get_html(self, url: str) -> str:
        return request_html(url).decode("utf-8")

    def test_page(self):
        self.check_OK("/chatbot")

    def test_page_with_session(self):
        resp = json_request_return_dict(
            "/api/chatbot/send", method="POST",
            data=dict(session_id=0, content="页面测试"))
        session_id = resp["data"]["session"]["session_id"]

        self.check_OK("/chatbot?session_id=%s" % session_id)

    def test_page_has_aside(self):
        html = self.get_html("/chatbot")
        assert "应用中心" in html

    def test_new_session_not_selected(self):
        # 先产生一个已有会话, 否则没有会话可选, 测不出差异
        json_request_return_dict(
            "/api/chatbot/send", method="POST",
            data=dict(session_id=0, content="已有会话"))

        # 默认进入时自动选中最近的一个会话
        assert "chat-session-item active" in self.get_html("/chatbot")
        # action=new 时不应选中任何会话, 消息区留空
        new_html = self.get_html("/chatbot?action=new")
        assert "chat-session-item active" not in new_html
        assert "chat-empty-tip" in new_html
        assert 'id="current-session-id" value="0"' in new_html

    def test_new_session_link_points_to_action_new(self):
        html = self.get_html("/chatbot")
        assert "/chatbot?action=new" in html

    def test_page_has_delete_button(self):
        # 桌面端会话列表项带删除按钮
        assert "chat-session-delete" in self.get_html("/chatbot")

    def test_mobile_template_is_wired(self):
        # render_by_ua 在移动端 UA 下应自动选中 .mobile.html
        mobile = xtemplate.get_mobile_template("chatbot/page/chatbot.html")
        assert mobile == "chatbot/page/chatbot.mobile.html"

    def test_mobile_page_renders(self):
        session = ChatSessionRecord()
        session.session_id = 1
        session.title = "移动端会话"
        session.last_message = "摘要"
        msg = ChatMessageRecord()
        msg.content = "你好"
        msg.create_time = 0
        msg.sender_type = SenderType.user

        html = xtemplate.render(
            "chatbot/page/chatbot.mobile.html",
            title="聊天助手",
            parent_link=None,
            session_list=[session],
            current_session=session,
            current_session_id=1,
            message_list=[msg],
            aside_html="",
        ).decode("utf-8")

        assert "chat-mobile" in html
        assert "chat-session-drawer" in html
        # 移动端同样通过 include 渲染删除按钮
        assert "chat-session-delete" in html
        # 当前会话标题应渲染出来
        assert "移动端会话" in html
