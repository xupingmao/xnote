# -*- coding:utf-8 -*-
"""聊天的业务逻辑层(通用层, 不感知"机器人"概念)

设计约定见 models.py 文件头
"""

from typing import Optional

from xutils import textutil

from . import dao
from .models import (ChatMessageRecord, ChatSessionRecord, MessageListResult,
                     MsgType, SenderType, SessionListResult)

# 会话列表里展示的消息摘要长度
SUMMARY_LENGTH = 50


class ChatService:
    """通用的聊天服务"""

    @classmethod
    def create_session(cls, user_id: int, chat_type: str,
                       title: str = "") -> ChatSessionRecord:
        record = ChatSessionRecord()
        record.user_id = user_id
        record.chat_type = chat_type
        record.title = title
        session_id = dao.ChatSessionDao.create(record)
        record.session_id = session_id
        return record

    @classmethod
    def get_session(cls, session_id: int,
                    user_id: int) -> Optional[ChatSessionRecord]:
        """读取会话并校验归属, 不属于该用户时返回 None"""
        record = dao.ChatSessionDao.get_by_id(session_id)
        if record is None:
            return None
        if record.user_id != user_id:
            return None
        return record

    @classmethod
    def get_or_create_session(cls, session_id: int, user_id: int,
                              chat_type: str) -> ChatSessionRecord:
        """读取会话, 不存在或无权访问时创建新会话"""
        if session_id > 0:
            record = cls.get_session(session_id, user_id)
            if record is not None:
                return record
        return cls.create_session(user_id, chat_type)

    @classmethod
    def list_sessions(cls, user_id: int, chat_type: str = "",
                      offset: int = 0, limit: int = 50) -> SessionListResult:
        result = SessionListResult()
        result.sessions = dao.ChatSessionDao.list_by_user(
            user_id, chat_type, offset, limit)
        result.total = dao.ChatSessionDao.count_by_user(user_id, chat_type)
        return result

    @classmethod
    def build_message(cls, session_id: int, sender_type: str, sender_id: int,
                      content: str) -> ChatMessageRecord:
        record = ChatMessageRecord()
        record.session_id = session_id
        record.sender_type = sender_type
        record.sender_id = sender_id
        record.msg_type = MsgType.text
        record.content = content
        return record

    @classmethod
    def send_message(cls, session_id: int, sender_type: str, sender_id: int,
                     content: str) -> ChatMessageRecord:
        """写入一条消息并刷新会话摘要"""
        record = cls.build_message(session_id, sender_type, sender_id, content)
        message_id = dao.ChatMessageDao.create(record)
        record.message_id = message_id
        cls.update_session_summary(session_id, sender_type, content)
        return record

    @classmethod
    def update_session_summary(cls, session_id: int, sender_type: str,
                               content: str) -> None:
        """刷新会话的最后消息摘要, 会话无标题时用首条用户消息作为标题"""
        session = dao.ChatSessionDao.get_by_id(session_id)
        if session is None:
            return

        summary = textutil.get_short_text(content, SUMMARY_LENGTH)
        session.last_message = summary
        if session.title == "" and sender_type == SenderType.user:
            session.title = summary
        dao.ChatSessionDao.update(session)

    @classmethod
    def list_messages(cls, session_id: int, offset: int = 0,
                      limit: int = 50) -> MessageListResult:
        result = MessageListResult()
        result.messages = dao.ChatMessageDao.list_by_session(
            session_id, offset, limit)
        result.total = dao.ChatMessageDao.count_by_session(session_id)
        return result

    @classmethod
    def delete_session(cls, session_id: int, user_id: int) -> bool:
        session = cls.get_session(session_id, user_id)
        if session is None:
            return False
        dao.ChatMessageDao.delete_by_session(session_id)
        dao.ChatSessionDao.delete_by_id(session_id, user_id)
        return True
