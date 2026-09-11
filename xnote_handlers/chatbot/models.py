# -*- coding:utf-8 -*-
"""聊天模块的数据模型(通用层)

设计约定(重要):
1. 本文件与 dao.py/chat_service.py 属于通用聊天层, 不感知"机器人"概念,
   机器人相关的逻辑放在 reply_engine.py/chatbot_service.py
2. 通用层禁止 import xnote_handlers 下的任何模块, 只允许依赖
   xnote.core.xtables / xutils.base / xutils.dateutil / xutils.textutil
   目的: 未来抽出独立的聊天包时可以直接整体搬迁, 无需处理依赖
3. 类型字段使用普通常量类而不是 Enum, 方便外部扩展
   (参考 xnote/service/comment_service.py)
"""

from typing import List, Optional

from xutils import dateutil
from xutils.base import BaseDataRecord


class ChatType:
    """会话类型"""
    bot = "bot"      # 人机会话
    user = "user"    # 用户间会话(预留)


class SenderType:
    """发送者类型(与"机器人"解耦)"""
    user = "user"
    bot = "bot"
    system = "system"


class MsgType:
    """消息类型"""
    text = "text"


class MsgStatus:
    """消息/会话状态"""
    normal = 0
    deleted = 1


class ChatSessionRecord(BaseDataRecord):
    """聊天会话"""

    _ignore_save_fields = ["session_id"]

    def __init__(self):
        super().__init__()
        self.session_id = 0
        self.create_time = 0
        self.update_time = 0
        self.chat_type = ChatType.bot
        self.title = ""
        self.status = MsgStatus.normal
        self.user_id = 0
        self.last_message = ""

    @property
    def ctime_str(self) -> str:
        if self.create_time > 0:
            return dateutil.format_datetime(self.create_time / 1000)
        return ""


class ChatMessageRecord(BaseDataRecord):
    """聊天消息"""

    _ignore_save_fields = ["message_id"]

    def __init__(self):
        super().__init__()
        self.message_id = 0
        self.create_time = 0
        self.update_time = 0
        self.session_id = 0
        self.sender_type = SenderType.user
        self.sender_id = 0
        self.msg_type = MsgType.text
        self.content = ""
        self.status = MsgStatus.normal

    @property
    def time_str(self) -> str:
        """展示用的时间(HH:MM:SS)"""
        if self.create_time > 0:
            return dateutil.format_time_only(self.create_time / 1000)
        return ""

    @property
    def is_bot(self) -> bool:
        return self.sender_type == SenderType.bot


class SessionListResult(BaseDataRecord):
    """会话列表结果"""

    def __init__(self):
        self.sessions: List[ChatSessionRecord] = []
        self.total = 0


class MessageListResult(BaseDataRecord):
    """消息列表结果"""

    def __init__(self):
        self.messages: List[ChatMessageRecord] = []
        self.total = 0


class SendMessageResult(BaseDataRecord):
    """发送消息的结果"""

    def __init__(self):
        self.session: Optional[ChatSessionRecord] = None
        self.message: Optional[ChatMessageRecord] = None
        # 机器人的回复, 非机器人会话时为 None
        self.reply: Optional[ChatMessageRecord] = None
        # 最新的会话列表, 用于前端刷新侧边栏
        self.session_list: List[ChatSessionRecord] = []
        # 前端命令列表, 配合 xnote.executeCommands 使用
        # (append_html / update_html / update_value 等)
        self.commands = []
