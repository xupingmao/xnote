# -*- coding:utf-8 -*-
"""聊天机器人的业务逻辑(机器人专用层, 编排通用聊天能力与规则引擎)"""

from . import reply_engine
from . import chatbot_render
from .chat_service import ChatService
from .models import ChatType, SendMessageResult, SenderType


class ChatBotService:
    """聊天机器人服务"""

    @classmethod
    def send(cls, user_id: int, user_name: str, session_id: int,
             content: str) -> SendMessageResult:
        """保存用户消息, 生成机器人回复并保存"""
        is_new_session = session_id <= 0
        session = ChatService.get_or_create_session(
            session_id, user_id, ChatType.bot)
        message = ChatService.send_message(
            session.session_id, SenderType.user, user_id, content)

        ctx = reply_engine.build_context(
            user_id=user_id,
            user_name=user_name,
            session_id=session.session_id,
            content=content)
        result = reply_engine.reply(ctx)

        reply_message = None
        if result.content != "":
            reply_message = ChatService.send_message(
                session.session_id, SenderType.bot, 0, result.content)

        send_result = SendMessageResult()
        # 重新读取, 使标题与摘要反映最新的消息
        send_result.session = ChatService.get_session(session.session_id, user_id)
        send_result.message = message
        send_result.reply = reply_message

        # 最新的会话列表(左侧栏刷新用)
        send_result.session_list = ChatService.list_sessions(
            user_id, ChatType.bot).sessions

        # 构造前端命令, 交由 xnote.executeCommands 执行
        send_result.commands = chatbot_render.build_send_commands(
            send_result, is_new_session)
        return send_result
