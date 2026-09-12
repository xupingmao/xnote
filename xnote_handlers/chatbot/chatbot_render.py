# -*- coding:utf-8 -*-
"""聊天机器人页面的后端渲染

把消息行 / 会话列表等 HTML 片段放在后端用模板渲染(小模板直接内联在 Python 里,
用 xtemplate.render_text 渲染), 前端只负责通过 xnote.executeCommands 执行下发的命令
(append_html / update_html / update_value 等), 从而减少前端渲染代码、避免 XSS。

会话列表项里的操作(置顶/重命名/删除)通过 MoreActionsMenu 组件收纳成一个"更多"菜单。
"""

from typing import List

from xnote.core import xtemplate
from xnote.webui import MenuItem, MoreActionsMenu
from xutils import webutil

from .models import ChatMessageRecord, ChatSessionRecord, SendMessageResult


def _to_text(html) -> str:
    """xtemplate.render / render_text 返回 bytes, 命令的 value 需要是文本"""
    if isinstance(html, bytes):
        return html.decode("utf-8")
    return html


# 小于20行的小模板直接内联在 Python 中, 用 render_text 渲染
_MESSAGE_ROWS_TEMPLATE = '''
{% for msg in message_list %}
<div class="chat-message-row{% if msg.is_bot %} chat-message-bot{% else %} chat-message-user{% end %}">
  <div class="chat-message-bubble">{{msg.content}}</div>
  <div class="chat-message-time">{{msg.time_str}}</div>
</div>
{% end %}
'''

_SESSION_LIST_TEMPLATE = '''
{% for item in rows %}
<div class="chat-session-item{% if item['active'] %} active{% end %}" data-title="{{item['real_title']}}">
  <a class="chat-session-link" href="{{_server_home}}/chatbot?session_id={{item['session_id']}}">
    <div class="chat-session-title">{% if item['is_top'] %}📌 {% end %}{{item['title']}}</div>
    <div class="chat-session-desc">{{item['last_message']}}</div>
  </a>
  {% raw item['menu_html'] %}
</div>
{% end %}
'''


def render_message_rows(message_list: List[ChatMessageRecord]) -> str:
    """渲染一组消息行(用于追加到消息区)"""
    return _to_text(xtemplate.render_text(_MESSAGE_ROWS_TEMPLATE,
                                          message_list=message_list))


def render_session_list(session_list: List[ChatSessionRecord],
                        current_session_id: int = 0) -> str:
    """渲染会话列表项(不含"新建会话"入口), 操作收纳进"更多"菜单"""
    rows = []
    for item in session_list:
        active = bool(current_session_id and item.session_id == current_session_id)
        menu_items = [
            MenuItem("取消置顶" if item.is_top else "置顶",
                     "chat-session-top", item.session_id, item.is_top),
            MenuItem("重命名", "chat-session-rename", item.session_id),
            MenuItem("删除", "chat-session-delete", item.session_id),
        ]
        rows.append({
            "session_id": item.session_id,
            "title": item.title or "新会话",
            "real_title": item.title,
            "is_top": item.is_top,
            "last_message": item.last_message,
            "active": active,
            "menu_html": MoreActionsMenu(menu_items).render(),
        })
    return _to_text(xtemplate.render_text(_SESSION_LIST_TEMPLATE, rows=rows))


# 空消息区提示(与页面模板里的初始空状态一致)
_EMPTY_MESSAGE_HTML = ('<div class="chat-empty-tip" id="chat-empty-tip">'
                       '新会话, 发送第一条消息后自动创建</div>')


def build_session_list_command(session_list: List[ChatSessionRecord],
                               current_session_id: int = 0
                               ) -> webutil.CommandItem:
    """构造刷新左侧会话列表的命令(update_html)

    会话的增删改后都通过它把左侧列表交给前端 executeCommands 更新, 不在前端手写 DOM。
    """
    return webutil.CommandItem(
        command="update_html", id="session-list-inner",
        value=render_session_list(session_list, current_session_id))


def build_empty_state_commands() -> List[webutil.CommandItem]:
    """当前会话被删除后, 把右侧消息区/标题/隐藏会话ID重置为空状态

    用已有的 update_html / update_value / update_text 命令表示, 无需新增命令类型。
    """
    return [
        webutil.CommandItem(command="update_html", id="message-list",
                             value=_EMPTY_MESSAGE_HTML),
        webutil.CommandItem(command="update_value", id="current-session-id",
                             value=0),
        webutil.CommandItem(command="update_text", id="chat-mobile-title",
                             value="聊天助手"),
    ]


def build_send_commands(result: SendMessageResult,
                        is_new_session: bool) -> List[webutil.CommandItem]:
    """根据发送结果构造前端命令列表

    - 新会话: 用 update_html 整体替换消息区(顺带移除空提示),
      并刷新隐藏的会话ID与左侧会话列表
    - 已有会话: 用 append_html 追加新消息

    命令统一用 webutil.CommandItem 构造(不要直接拼 dict)。
    """
    commands: List[webutil.CommandItem] = []

    rows: List[ChatMessageRecord] = []
    if result.message is not None:
        rows.append(result.message)
    if result.reply is not None:
        rows.append(result.reply)

    fragment = render_message_rows(rows)

    if is_new_session:
        commands.append(webutil.CommandItem(
            command="update_html", id="message-list", value=fragment))
    else:
        commands.append(webutil.CommandItem(
            command="append_html", id="message-list", value=fragment))

    if result.session is not None:
        commands.append(webutil.CommandItem(
            command="update_value", id="current-session-id",
            value=result.session.session_id))
        commands.append(webutil.CommandItem(
            command="update_html", id="session-list-inner",
            value=render_session_list(result.session_list,
                                      result.session.session_id)))
        # 同步移动端标题(桌面端无该元素, update_text 自动忽略)
        commands.append(webutil.CommandItem(
            command="update_text", id="chat-mobile-title",
            value=result.session.title))

    return commands
