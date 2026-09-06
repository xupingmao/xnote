# -*- coding: utf-8 -*-
"""xnote-cli 会话持久化

负责把登录后的会话信息（服务端地址、用户名、会话 cookie、远程命令列表）保存到
${user_home}/.xnote-cli/session.json，并在需要时读取。

会话使用结构化的 `SessionInfo` 对象表示，对外通过 `to_dict` / `from_dict`
与 JSON 互转，避免在业务代码里直接操作裸 dict。
"""
import os
import json
from typing import Dict, Optional

DEFAULT_SESSION_PATH = os.path.join(
    os.path.expanduser("~"), ".xnote-cli", "session.json")


class SessionInfo:
    """登录后的会话信息（结构化对象，替代裸 dict）

    Attributes:
        server_url: 服务端地址
        username: 登录用户名
        cookie: 会话 cookie（sid;sid_list），请求时放在 Cookie 头
        commands: 服务端远程命令列表（name -> help），登录时缓存
    """

    def __init__(self, server_url="", username="", cookie="", commands=None):
        # type: (str, str, str, Optional[Dict[str, str]]) -> None
        self.server_url = server_url
        self.username = username
        self.cookie = cookie
        self.commands = commands if commands is not None else {}  # type: Dict[str, str]

    def to_dict(self):
        # type: () -> dict
        return {
            "server_url": self.server_url,
            "username": self.username,
            "cookie": self.cookie,
            "commands": self.commands,
        }

    @staticmethod
    def from_dict(d):
        # type: (Optional[dict]) -> SessionInfo
        if not isinstance(d, dict):
            d = {}
        commands = d.get("commands")
        if not isinstance(commands, dict):
            commands = {}
        return SessionInfo(
            server_url=d.get("server_url", "") or "",
            username=d.get("username", "") or "",
            cookie=d.get("cookie", "") or "",
            commands=commands,
        )


def get_session_path():
    # type: () -> str
    return DEFAULT_SESSION_PATH


def load_session():
    # type: () -> Optional[SessionInfo]
    path = get_session_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as fp:
            return SessionInfo.from_dict(json.load(fp))
    except Exception:
        return None


def save_session(session):
    # type: (SessionInfo) -> None
    """保存会话对象到本地文件；传入空的 SessionInfo() 相当于清空会话"""
    path = get_session_path()
    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    data = session.to_dict() if isinstance(session, SessionInfo) else session
    with open(path, "w") as fp:
        json.dump(data, fp)
