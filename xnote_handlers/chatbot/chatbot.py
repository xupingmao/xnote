# -*- coding:utf-8 -*-
"""聊天机器人的页面"""

from typing import List, Optional

import xutils
from xnote.core import xauth, xtemplate
from xutils import Storage

from xnote_handlers.config import AsideConfig, LinkConfig

from . import chatbot_render
from .chat_service import ChatService
from .models import ChatMessageRecord, ChatSessionRecord, ChatType

SESSION_LIMIT = 100
MESSAGE_LIMIT = 200

# 新建会话, 不选中已有会话
ACTION_NEW = "new"


class ChatBotHandler:
    """聊天机器人主页"""

    @xauth.login_required()
    def GET(self):
        user_id = xauth.current_user_id()
        session_id = xutils.get_argument_int("session_id", 0)
        action = xutils.get_argument_str("action")

        session_result = ChatService.list_sessions(
            user_id, ChatType.bot, limit=SESSION_LIMIT)

        current = self.get_current_session(action, session_id, user_id,
                                           session_result.sessions)
        message_list: List[ChatMessageRecord] = []
        if current is not None:
            message_list = ChatService.list_messages(
                current.session_id, limit=MESSAGE_LIMIT).messages

        kw = Storage()
        kw.title = "聊天助手"
        kw.parent_link = LinkConfig.app_index
        kw.session_list_html = chatbot_render.render_session_list(
            session_result.sessions,
            current.session_id if current else 0)
        kw.current_session = current
        kw.current_session_id = current.session_id if current else 0
        kw.message_list = message_list
        kw.aside_html = AsideConfig.default_aside_html
        return xtemplate.render_by_ua("chatbot/page/chatbot.html", **kw)

    def get_current_session(self, action: str, session_id: int, user_id: int,
                            session_list: List[ChatSessionRecord]
                            ) -> Optional[ChatSessionRecord]:
        """确定当前会话

        action=new 时不选中任何会话, 消息区留空,
        会话由前端在首次发送时创建(发送接口支持 session_id=0)
        其他情况未指定会话时取最近的一个
        """
        if action == ACTION_NEW:
            return None

        if session_id > 0:
            session = ChatService.get_session(session_id, user_id)
            if session is not None:
                return session

        if len(session_list) > 0:
            return session_list[0]
        return None


xurls = (
    r"/chatbot", ChatBotHandler,
)
