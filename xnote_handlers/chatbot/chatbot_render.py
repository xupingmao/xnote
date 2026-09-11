# -*- coding:utf-8 -*-
"""聊天机器人页面的后端渲染

把消息行 / 会话列表等 HTML 片段放在后端用模板渲染,
前端只负责通过 xnote.executeCommands 执行下发的命令(append_html /
update_html / update_value 等), 从而减少前端渲染代码、避免 XSS。
"""

from typing import Any, Dict, List, Optional

from xnote.core import xtemplate

from .models import ChatMessageRecord, ChatSessionRecord, SendMessageResult


def _to_text(html) -> str:
    """xtemplate.render 返回 bytes, 命令的 value 需要是文本"""
    if isinstance(html, bytes):
        return html.decode("utf-8")
    return html


def render_message_rows(message_list: List[ChatMessageRecord]) -> str:
    """渲染一组消息行(用于追加到消息区)"""
    return _to_text(xtemplate.render("chatbot/component/message_rows.html",
                                     message_list=message_list))


def render_session_list(session_list: List[ChatSessionRecord],
                        current_session_id: int = 0) -> str:
    """渲染会话列表项(不含"新建会话"入口)"""
    return _to_text(xtemplate.render("chatbot/component/session_list.html",
                                     session_list=session_list,
                                     current_session_id=current_session_id))


def build_send_commands(result: SendMessageResult,
                        is_new_session: bool) -> List[Dict[str, Any]]:
    """根据发送结果构造前端命令列表

    - 新会话: 用 update_html 整体替换消息区(顺带移除空提示),
      并刷新隐藏的会话ID与左侧会话列表
    - 已有会话: 用 append_html 追加新消息
    """
    commands: List[Dict[str, Any]] = []

    rows: List[ChatMessageRecord] = []
    if result.message is not None:
        rows.append(result.message)
    if result.reply is not None:
        rows.append(result.reply)

    fragment = render_message_rows(rows)

    if is_new_session:
        commands.append({
            "command": "update_html",
            "id": "message-list",
            "value": fragment,
        })
    else:
        commands.append({
            "command": "append_html",
            "id": "message-list",
            "value": fragment,
        })

    if result.session is not None:
        commands.append({
            "command": "update_value",
            "id": "current-session-id",
            "value": result.session.session_id,
        })
        commands.append({
            "command": "update_html",
            "id": "session-list-inner",
            "value": render_session_list(result.session_list,
                                         result.session.session_id),
        })

    return commands
