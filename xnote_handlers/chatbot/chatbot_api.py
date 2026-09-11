# -*- coding:utf-8 -*-
"""聊天机器人的REST接口"""

import xutils
from xnote.core import xauth
from xutils import webutil

from .chat_service import ChatService
from .chatbot_service import ChatBotService
from .dao import DEFAULT_LIMIT
from .models import ChatType

VALID_CHAT_TYPES = (ChatType.bot, ChatType.user)


def check_chat_type(chat_type: str) -> str:
    """校验会话类型, 非法值回退到机器人会话"""
    if chat_type in VALID_CHAT_TYPES:
        return chat_type
    return ChatType.bot


class SessionListHandler:
    """会话列表"""

    @xauth.login_required()
    def GET(self):
        user_id = xauth.current_user_id()
        chat_type = check_chat_type(xutils.get_argument_str("chat_type"))
        offset = xutils.get_argument_int("offset")
        limit = xutils.get_argument_int("limit", DEFAULT_LIMIT)

        result = ChatService.list_sessions(
            user_id, chat_type, offset=offset, limit=limit)
        return webutil.SuccessResult(data=result)


class SessionCreateHandler:
    """创建会话"""

    @xauth.login_required()
    def POST(self):
        user_id = xauth.current_user_id()
        title = xutils.get_argument_str("title")
        chat_type = check_chat_type(
            xutils.get_argument_str("chat_type", ChatType.bot))

        session = ChatService.create_session(user_id, chat_type, title)
        return webutil.SuccessResult(data=session)


class SessionDeleteHandler:
    """删除会话"""

    @xauth.login_required()
    def POST(self):
        user_id = xauth.current_user_id()
        session_id = xutils.get_argument_int("session_id")

        if session_id <= 0:
            return webutil.FailedResult(code="400", message="会话ID不合法")

        if not ChatService.delete_session(session_id, user_id):
            return webutil.FailedResult(code="404", message="会话不存在")
        return webutil.SuccessResult(message="删除成功")


class MessageListHandler:
    """消息列表"""

    @xauth.login_required()
    def GET(self):
        user_id = xauth.current_user_id()
        session_id = xutils.get_argument_int("session_id")
        offset = xutils.get_argument_int("offset")
        limit = xutils.get_argument_int("limit", DEFAULT_LIMIT)

        if ChatService.get_session(session_id, user_id) is None:
            return webutil.FailedResult(code="404", message="会话不存在")

        result = ChatService.list_messages(session_id, offset=offset, limit=limit)
        return webutil.SuccessResult(data=result)


class SendMessageHandler:
    """发送消息并获取机器人回复"""

    @xauth.login_required()
    def POST(self):
        user_id = xauth.current_user_id()
        user_name = xauth.current_name_str()
        session_id = xutils.get_argument_int("session_id")
        content = xutils.get_argument_str("content")

        if content == "":
            return webutil.FailedResult(code="400", message="消息内容不能为空")

        if session_id > 0 and ChatService.get_session(session_id, user_id) is None:
            return webutil.FailedResult(code="404", message="会话不存在")

        result = ChatBotService.send(user_id, user_name, session_id, content)
        return webutil.SuccessResult(data=result)


xurls = (
    r"/api/chatbot/session/list", SessionListHandler,
    r"/api/chatbot/session/create", SessionCreateHandler,
    r"/api/chatbot/session/delete", SessionDeleteHandler,
    r"/api/chatbot/message/list", MessageListHandler,
    r"/api/chatbot/send", SendMessageHandler,
)
