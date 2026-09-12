# -*- coding:utf-8 -*-
"""聊天模块的数据访问层(通用层, 不感知"机器人"概念)

设计约定见 models.py 文件头
"""

from typing import Any, Dict, List, Optional

from xnote.core import xtables
from xutils import dateutil

from .models import ChatMessageRecord, ChatSessionRecord, MsgStatus

# 单次读取的最大条数, 防止外部传入过大的 limit 打垮数据库
MAX_LIMIT = 1000
# 未指定或非法 limit 时使用的条数
DEFAULT_LIMIT = 50


def check_limit(limit: int) -> int:
    """校验读取条数, 保证落在 [1, MAX_LIMIT] 区间

    limit 小于等于0表示未指定, 使用默认值; 超过 MAX_LIMIT 时截断到 MAX_LIMIT
    """
    if limit <= 0:
        return DEFAULT_LIMIT
    if limit > MAX_LIMIT:
        return MAX_LIMIT
    return limit


def check_offset(offset: int) -> int:
    """校验偏移量, 负数会导致底层断言失败, 这里统一归零"""
    if offset < 0:
        return 0
    return offset


class ChatSessionDao:
    """聊天会话Dao"""

    db = xtables.get_table_by_name("chat_session")

    @classmethod
    def get_by_id(cls, session_id: int) -> Optional[ChatSessionRecord]:
        record = cls.db.select_first(where=dict(session_id=session_id))
        return ChatSessionRecord.from_dict_or_None(record)

    @classmethod
    def list_by_user(cls, user_id: int, chat_type: str = "",
                     offset: int = 0, limit: int = DEFAULT_LIMIT) -> List[ChatSessionRecord]:
        where: Dict[str, Any] = dict(user_id=user_id, status=MsgStatus.normal)
        if chat_type != "":
            where["chat_type"] = chat_type

        results = cls.db.select(where=where, offset=check_offset(offset),
                                limit=check_limit(limit),
                                order="is_top desc, update_time desc")
        return ChatSessionRecord.from_dict_list(results)

    @classmethod
    def count_by_user(cls, user_id: int, chat_type: str = "") -> int:
        where: Dict[str, Any] = dict(user_id=user_id, status=MsgStatus.normal)
        if chat_type != "":
            where["chat_type"] = chat_type
        return cls.db.count(where=where)

    @classmethod
    def create(cls, record: ChatSessionRecord) -> int:
        current_ms = dateutil.timestamp_ms()
        record.create_time = current_ms
        record.update_time = current_ms
        return cls.db.insert(**record.to_save_dict())

    @classmethod
    def update(cls, record: ChatSessionRecord) -> int:
        record.update_time = dateutil.timestamp_ms()
        return cls.db.update(where=dict(session_id=record.session_id),
                             **record.to_save_dict())

    @classmethod
    def delete_by_id(cls, session_id: int, user_id: int) -> int:
        return cls.db.delete(where=dict(session_id=session_id, user_id=user_id))


class ChatMessageDao:
    """聊天消息Dao"""

    db = xtables.get_table_by_name("chat_message")

    @classmethod
    def get_by_id(cls, message_id: int) -> Optional[ChatMessageRecord]:
        record = cls.db.select_first(where=dict(message_id=message_id))
        return ChatMessageRecord.from_dict_or_None(record)

    @classmethod
    def list_by_session(cls, session_id: int, offset: int = 0,
                        limit: int = DEFAULT_LIMIT) -> List[ChatMessageRecord]:
        results = cls.db.select(where=dict(session_id=session_id, status=MsgStatus.normal),
                                offset=check_offset(offset),
                                limit=check_limit(limit),
                                order="message_id asc")
        return ChatMessageRecord.from_dict_list(results)

    @classmethod
    def list_recent(cls, session_id: int, limit: int = DEFAULT_LIMIT) -> List[ChatMessageRecord]:
        """按时间正序返回最近的N条消息"""
        results = cls.db.select(where=dict(session_id=session_id, status=MsgStatus.normal),
                                limit=check_limit(limit), order="message_id desc")
        message_list = ChatMessageRecord.from_dict_list(results)
        return list(reversed(message_list))

    @classmethod
    def count_by_session(cls, session_id: int) -> int:
        return cls.db.count(where=dict(session_id=session_id, status=MsgStatus.normal))

    @classmethod
    def create(cls, record: ChatMessageRecord) -> int:
        current_ms = dateutil.timestamp_ms()
        record.create_time = current_ms
        record.update_time = current_ms
        return cls.db.insert(**record.to_save_dict())

    @classmethod
    def delete_by_id(cls, message_id: int) -> int:
        return cls.db.delete(where=dict(message_id=message_id))

    @classmethod
    def delete_by_session(cls, session_id: int) -> int:
        return cls.db.delete(where=dict(session_id=session_id))
