# -*- coding: utf-8 -*-
"""xnote-cli 本地（客户端）命令实现

说明：
- 本地命令在 CLI 客户端本地解析并执行，包括登录、退出、版本、帮助等。
- 笔记查看/搜索/编辑/删除、备份、修复、同步等“远程命令”由服务端插件提供，
  客户端登录后从 /api/cli/command_list 获取命令列表（并缓存到会话），
  执行时通过 /api/cli/run 转发到服务端。详见 xnote_cli/__init__.py 的 main()。
"""
import sys
import json
import getpass
import urllib.request
import urllib.error
from typing import Optional

import xnote_cli
from xnote_cli import (
    XnoteCliContext,
    register_cmd,
    print_result,
    save_session,
    load_session,
    _extract_session_cookie,
    get_server_url,
    _get_server_commands,
)
from xnote_cli.session import SessionInfo


def get_password(prompt="密码: "):
    # type: (str) -> str
    """读取密码并逐字符回显 *，让用户知道输入了几位

    Windows 用 msvcrt 逐字符读取；其他平台退化为 getpass（不回显）。
    """
    try:
        import msvcrt
    except ImportError:
        return getpass.getpass(prompt)
    sys.stdout.write(prompt)
    sys.stdout.flush()
    chars = []  # type: list
    while True:
        ch = msvcrt.getwch()
        if ch in ("\r", "\n"):
            sys.stdout.write("\n")
            break
        elif ch == "\x03":  # Ctrl-C
            raise KeyboardInterrupt
        elif ch == "\b":  # 退格
            if chars:
                chars.pop()
                sys.stdout.write("\b \b")
                sys.stdout.flush()
        elif ch in ("\x00", "\xe0"):  # 功能键前缀，忽略
            continue
        else:
            chars.append(ch)
            sys.stdout.write("*")
            sys.stdout.flush()
    return "".join(chars)


def do_login(ctx):
    # type: (XnoteCliContext) -> int
    name = input("用户名: ").strip()
    pswd = get_password("密码: ").strip()

    server_url = get_server_url(ctx)
    url = server_url + "/api/cli/login"
    body = json.dumps({"username": name, "password": pswd}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        set_cookie = ", ".join(resp.headers.get_all("Set-Cookie") or [])
        raw = resp.read()
    except urllib.error.HTTPError as e:
        set_cookie = ", ".join(e.headers.get_all("Set-Cookie") or [])
        raw = e.read()

    resp_dict = json.loads(raw.decode("utf-8", "ignore"))
    if resp_dict.get("success"):
        # 优先使用响应体回传的 sid 构造 Cookie（测试环境不下发 Set-Cookie），
        # 旧版服务端没有 sid 时回退到从 Set-Cookie 头解析
        data = resp_dict.get("data") or {}
        sid = data.get("sid") or ""
        if sid:
            cookie = "sid=%s" % sid
        else:
            cookie = _extract_session_cookie(set_cookie) or ""
        session = SessionInfo(server_url=server_url, username=name, cookie=cookie)
        save_session(session)
        # 登录成功后从服务端缓存远程命令列表，后续分发/帮助直接复用
        ctx.session = session
        ctx.server_url = server_url
        session.commands = _get_server_commands(ctx)
        save_session(session)
        print("登录成功: %s" % name)
        return 0
    print("登录失败: %s" % (resp_dict.get("message") or "未知错误"))
    return 1


def do_logout(ctx):
    # type: (XnoteCliContext) -> int
    resp = xnote_cli.request(ctx, "POST", "/api/cli/logout")
    xnote_cli.save_session(SessionInfo())  # 清空会话
    print("已退出登录")
    return print_result(resp)


def do_version(ctx):
    # type: (XnoteCliContext) -> int
    print("xnote-cli %s" % xnote_cli.VERSION)
    return 0


def do_help(ctx):
    # type: (XnoteCliContext) -> int
    xnote_cli._print_help()
    return 0


def do_session(ctx):
    # type: (XnoteCliContext) -> int
    # 直接输出当前会话信息（JSON），方便排查登录状态/服务端地址
    session = load_session()
    if session is None or not session.username:
        print(json.dumps({"logged_in": False}, ensure_ascii=False, indent=2))
        return 0
    info = session.to_dict()
    info["logged_in"] = True
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


def do_refresh(ctx):
    # type: (XnoteCliContext) -> int
    # 重新从服务端拉取远程命令列表并更新会话缓存
    session = load_session()
    if session is None or not session.username:
        print("尚未登录，请先执行 `xnote-cli login`")
        return 1
    ctx.session = session
    ctx.server_url = get_server_url(ctx)
    commands = _get_server_commands(ctx)
    if not commands:
        print("刷新失败：无法从服务端获取命令列表，请确认已登录且服务可用")
        return 1
    session.commands = commands
    save_session(session)
    print("远程命令已刷新，共 %d 条" % len(commands))
    return 0


def register_builtin_commands():
    # type: () -> None
    # 仅注册“本地命令”，远程命令由服务端提供（插件注册 + /api/cli/command_list）
    register_cmd("login", do_login, "登录到 xnote 服务端")
    register_cmd("logout", do_logout, "退出登录")
    register_cmd("version", do_version, "查看版本号")
    register_cmd("list", do_help, "列出所有可用命令")
    register_cmd("help", do_help, "查看帮助信息")
    register_cmd("session", do_session, "查看当前会话信息（JSON）")
    register_cmd("refresh", do_refresh, "刷新远程命令列表")
