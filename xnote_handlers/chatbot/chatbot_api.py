# -*- coding:utf-8 -*-
"""聊天机器人的REST接口"""

import xutils
from xnote.core import xauth
from xutils import webutil

from .chat_service import ChatService
from .chatbot_service import ChatBotService
from . import chatbot_render
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
        current_session_id = xutils.get_argument_int("current_session_id")

        if session_id <= 0:
            return webutil.FailedResult(code="400", message="会话ID不合法")

        if not ChatService.delete_session(session_id, user_id):
            return webutil.FailedResult(code="404", message="会话不存在")

        # 后端重新渲染会话列表, 通过命令交给前端 executeCommands 更新 DOM
        session_list = ChatService.list_sessions(user_id, ChatType.bot).sessions
        commands = [chatbot_render.build_session_list_command(
            session_list, current_session_id)]
        if current_session_id == session_id:
            # 删除的是当前会话, 右侧消息区重置为空状态
            commands.extend(chatbot_render.build_empty_state_commands())
        return webutil.SuccessResult(data={"commands": commands})


class SessionRenameHandler:
    """重命名会话"""

    @xauth.login_required()
    def POST(self):
        user_id = xauth.current_user_id()
        session_id = xutils.get_argument_int("session_id")
        current_session_id = xutils.get_argument_int("current_session_id")
        title = xutils.get_argument_str("title").strip()

        if session_id <= 0:
            return webutil.FailedResult(code="400", message="会话ID不合法")
        if title == "":
            return webutil.FailedResult(code="400", message="标题不能为空")

        session = ChatService.rename_session(session_id, user_id, title)
        if session is None:
            return webutil.FailedResult(code="404", message="会话不存在")

        # 后端重新渲染会话列表, 通过命令交给前端 executeCommands 更新 DOM
        session_list = ChatService.list_sessions(user_id, ChatType.bot).sessions
        commands = [chatbot_render.build_session_list_command(
            session_list, current_session_id)]
        if current_session_id == session_id:
            # 当前会话同步移动端标题
            commands.append(webutil.CommandItem(
                command="update_text", id="chat-mobile-title", value=session.title))
        return webutil.SuccessResult(data={"commands": commands})


class SessionTopHandler:
    """置顶/取消置顶会话"""

    @xauth.login_required()
    def POST(self):
        user_id = xauth.current_user_id()
        session_id = xutils.get_argument_int("session_id")

        if session_id <= 0:
            return webutil.FailedResult(code="400", message="会话ID不合法")

        session = ChatService.top_session(session_id, user_id)
        if session is None:
            return webutil.FailedResult(code="404", message="会话不存在")

        # 刷新左侧会话列表(置顶项自动排到最前), 高亮保持当前会话
        current_session_id = xutils.get_argument_int("current_session_id")
        session_list = ChatService.list_sessions(user_id, ChatType.bot).sessions
        html = chatbot_render.render_session_list(session_list, current_session_id)
        commands = [webutil.CommandItem(
            command="update_html", id="session-list-inner", value=html)]
        return webutil.SuccessResult(
            data={"commands": commands, "is_top": session.is_top})


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
    r"/api/chatbot/session/rename", SessionRenameHandler,
    r"/api/chatbot/session/top", SessionTopHandler,
    r"/api/chatbot/message/list", MessageListHandler,
    r"/api/chatbot/send", SendMessageHandler,
)
