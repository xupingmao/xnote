# -*- coding: utf-8 -*-
"""xnote 命令行工具核心模块

设计目标：
- 核心逻辑都在 xnote_cli 模块下
- 通过 register_cmd 注册命令，插件可以动态注册新的命令
- 登录后会话信息保存在 ${user_home}/.xnote-cli/session.json

约定：
- 服务端接口由 xnote_handlers 提供，本模块只负责构造请求和解析结果
- 接口返回的 JSON 统一使用 success 字段表示是否成功
"""
from typing import Callable, Dict, List, Optional, Any, Tuple
import os
import sys
import re
import json
import argparse
import socket
import urllib.request
import urllib.parse
import urllib.error

from . import session
from .session import get_session_path, load_session, save_session, SessionInfo

VERSION = "1.0.0"

DEFAULT_SERVER_URL = "http://localhost:1234"

# 命令注册表: name -> CommandEntry
COMMANDS = {}  # type: Dict[str, CommandEntry]

# 用于缓存已注册的标记
_registered = False  # type: bool


class XnoteCliError(Exception):
    """可预期的错误，message 会直接展示给用户"""


class CommandEntry:
    """命令元数据"""

    def __init__(self, name, handler, help=""):
        # type: (str, Callable, str) -> None
        self.name = name
        self.handler = handler
        self.help = help


class ApiResult:
    """服务端接口的返回结果（结构化对象，替代裸 dict）

    所有通过 `request` / `request_json` 发送的 HTTP 请求都返回 `ApiResult`，
    业务代码通过 `resp.success` / `resp.code` / `resp.message` / `resp.data`
    访问结果，而不是用 `dict.get("success")` 这类松散写法。

    Attributes:
        success: 是否成功（对应服务端返回 JSON 的 success 字段）
        code: 错误码（成功时通常为空或 "success"）
        message: 提示/错误信息
        data: 业务数据（dict / list / 标量，可能为 None）
    """

    def __init__(self, success=False, code="", message="", data=None):
        # type: (bool, str, str, Any) -> None
        self.success = success
        self.code = code
        self.message = message
        self.data = data

    @staticmethod
    def from_dict(d):
        # type: (Optional[dict]) -> ApiResult
        if not isinstance(d, dict):
            d = {}
        return ApiResult(
            success=bool(d.get("success")),
            code=d.get("code", "") or "",
            message=(d.get("message") or d.get("error") or ""),
            data=d.get("data"),
        )


class XnoteCliContext:
    """命令行上下文，传递给每个命令处理函数

    Attributes:
        command: 当前匹配到的命令名称
        args: 命令后面的参数列表
        options: 解析后的选项（预留）
        server_url: 服务端地址
        session: 加载的会话信息（可能为 None）
    """

    def __init__(self, command="", args=None, options=None):
        # type: (str, Optional[List[str]], Optional[dict]) -> None
        self.command = command
        self.args = args if args is not None else []  # type: List[str]
        self.options = options if options is not None else {}  # type: dict
        self.server_url = ""  # type: str
        self.session = None  # type: Optional[SessionInfo]


def register_cmd(name, handler, help=""):
    # type: (str, Callable, Optional[str]) -> None
    """注册一个 cli 命令，插件可以动态调用本接口注册命令"""
    COMMANDS[name] = CommandEntry(name, handler, help or "")


def get_command(name):
    # type: (str) -> Optional[CommandEntry]
    return COMMANDS.get(name)


def list_commands():
    # type: () -> List[CommandEntry]
    result = list(COMMANDS.values())
    result.sort(key=lambda x: x.name)
    return result


# ---------------------------------------------------------------------------
# 会话管理（持久化逻辑见 xnote_cli/session.py）
# ---------------------------------------------------------------------------

def get_server_url(ctx):
    # type: (XnoteCliContext) -> str
    url = os.environ.get("XNOTE_CLI_URL", "")
    if url:
        return url.rstrip("/")
    if ctx.session:
        url = ctx.session.server_url
        if url:
            return url.rstrip("/")
    return DEFAULT_SERVER_URL


# ---------------------------------------------------------------------------
# HTTP 客户端
# ---------------------------------------------------------------------------

def _http_request(method, url, data=None, headers=None):
    # type: (str, str, Optional[bytes], Optional[dict]) -> Tuple[int, dict, bytes]
    req = urllib.request.Request(url, data=data, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return resp.getcode(), dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except (urllib.error.URLError, socket.timeout, ConnectionError) as e:
        # 连接失败：服务未启动或地址错误
        reason = getattr(e, "reason", e)
        raise XnoteCliError(
            "无法连接服务端 %s，请确认 xnote 服务已启动（默认地址 %s）"
            % (url, DEFAULT_SERVER_URL)) from e


def _extract_session_cookie(set_cookie):
    # type: (str) -> Optional[str]
    """从 Set-Cookie 响应头中提取会话 cookie

    服务端登录会同时设置 `sid`（鉴权用）和 `sid_list` 两个 cookie，
    这里把它们都提取出来拼成请求时使用的 Cookie 头。
    """
    if not set_cookie:
        return None
    found = re.findall(r"\b(sid_list|sid)=([^;]+)", set_cookie)
    if not found:
        return None
    return "; ".join("%s=%s" % (k, v.strip()) for k, v in found)


def _build_headers(ctx, content_type=None):
    # type: (XnoteCliContext, Optional[str]) -> dict
    headers = {"Accept": "application/json"}  # type: dict
    if content_type:
        headers["Content-Type"] = content_type
    if ctx.session and ctx.session.cookie:
        headers["Cookie"] = ctx.session.cookie
    return headers


def request(ctx, method, path, params=None, data=None):
    # type: (XnoteCliContext, str, str, Optional[dict], Optional[dict]) -> ApiResult
    """发送表单请求，返回结构化的 ApiResult"""
    server_url = get_server_url(ctx)
    url = server_url + path
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    body = None  # type: Optional[bytes]
    headers = _build_headers(ctx)
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    code, resp_headers, raw = _http_request(method, url, data=body, headers=headers)
    return _parse_response(code, resp_headers, raw)


def request_json(ctx, method, path, params=None, json_data=None):
    # type: (XnoteCliContext, str, str, Optional[dict], Optional[Any]) -> ApiResult
    """发送 JSON 请求，返回结构化的 ApiResult"""
    server_url = get_server_url(ctx)
    url = server_url + path
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    body = None  # type: Optional[bytes]
    headers = _build_headers(ctx, content_type="application/json")
    if json_data is not None:
        body = json.dumps(json_data).encode("utf-8")
    code, resp_headers, raw = _http_request(method, url, data=body, headers=headers)
    return _parse_response(code, resp_headers, raw)


def _parse_response(code, resp_headers, raw):
    # type: (int, dict, bytes) -> ApiResult
    content_type = resp_headers.get("Content-Type", "") if resp_headers else ""
    text = raw.decode("utf-8", errors="ignore")
    if not text:
        return ApiResult()
    stripped = text.lstrip()
    if ("text/html" in content_type
            or stripped.startswith("<!DOCTYPE")
            or stripped.startswith("<html")):
        # 服务端返回了 HTML 页面，通常是因为未登录被重定向到登录页
        return ApiResult(
            success=False,
            code="unauthorized",
            message="未登录或登录已失效，请先执行 `xnote-cli login` 登录后再试")
    try:
        return ApiResult.from_dict(json.loads(text))
    except Exception:
        return ApiResult(
            success=False,
            code="invalid_response",
            message="服务端返回了无法解析的响应（HTTP %s）" % code)


# ---------------------------------------------------------------------------
# 结果展示
# ---------------------------------------------------------------------------

def print_result(resp):
    # type: (ApiResult) -> int
    if not isinstance(resp, ApiResult):
        print(resp)
        return 0
    if resp.success:
        data = resp.data
        if data is not None:
            if isinstance(data, (dict, list)):
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                print(data)
        elif resp.message:
            print(resp.message)
        return 0
    message = resp.message or ""
    code = resp.code or ""
    if message:
        print("操作失败：%s" % message)
    elif code:
        print("操作失败（错误码：%s）" % code)
    else:
        print("操作失败，服务端未返回明确的错误信息")
    return 1


# ---------------------------------------------------------------------------
# 命令分发
# ---------------------------------------------------------------------------

def _match_command(argv):
    # type: (List[str]) -> Tuple[str, List[str]]
    for i in range(len(argv), 0, -1):
        name = " ".join(argv[:i])
        if name in COMMANDS:
            return name, argv[i:]
    return "", argv


def _print_help():
    # type: () -> None
    print("xnote-cli 使用说明")
    print("")
    print("本地命令:")
    for cmd in list_commands():
        print("  %-22s %s" % (cmd.name, cmd.help))

    # 远程命令（服务端插件提供，登录后从服务端获取）
    help_ctx = XnoteCliContext()
    help_ctx.session = load_session()
    remote_cmds = _load_remote_commands(help_ctx)
    if remote_cmds:
        print("")
        print("远程命令（服务端提供）:")
        for name in sorted(remote_cmds.keys()):
            print("  %-22s %s" % (name, remote_cmds[name]))
    else:
        print("")
        print("远程命令需要先登录后才会显示，请执行 `xnote-cli login`")
    print("")
    print("环境变量:")
    print("  XNOTE_CLI_URL  服务端地址，默认 %s" % DEFAULT_SERVER_URL)


def _get_server_commands(ctx):
    # type: (XnoteCliContext) -> Dict[str, str]
    """实时从服务端拉取远程命令列表（插件命令）"""
    try:
        resp = request(ctx, "GET", "/api/cli/command_list")
        if resp.success:
            data = resp.data or []
            return {item.get("name"): item.get("help", "") for item in data}
    except Exception:
        pass
    return {}


def _load_remote_commands(ctx):
    # type: (XnoteCliContext) -> Dict[str, str]
    """返回服务端远程命令列表（name -> help）

    优先使用登录时缓存到会话中的列表（见 do_login）；未登录或缓存为空时
    再尝试实时拉取。未登录会导致拉取失败，此时返回空 dict。
    """
    if ctx.session:
        cached = ctx.session.commands
        if isinstance(cached, dict) and len(cached) > 0:
            return cached
    return _get_server_commands(ctx)


def _forward_to_server(ctx, name, args):
    # type: (XnoteCliContext, str, List[str]) -> int
    """把命令转发给服务端执行（插件命令在服务端运行）"""
    resp = request(ctx, "POST", "/api/cli/run",
                   data={"cmd": name, "args": "\n".join(args)})
    if resp.success:
        data = resp.data
        if data:
            if isinstance(data, (dict, list)):
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                print(data)
        return 0
    message = resp.message or ""
    if message:
        print("命令执行失败：%s" % message)
    else:
        print("命令执行失败，服务端未返回有效结果")
    return 1


def _build_parser(ctx):
    # type: (XnoteCliContext) -> argparse.ArgumentParser
    """构建 argparse 解析器，为每个（本地 + 远程）子命令生成独立的 -h 帮助

    远程命令由服务端动态提供，仅在已登录（会话存在）时注册为子命令，
    避免每次调用都发起网络请求。
    """
    parser = argparse.ArgumentParser(
        prog="xnote-cli",
        description="xnote 命令行工具（本地命令在客户端执行，远程命令在服务端执行）")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    builtin_names = set()  # type: set
    for entry in list_commands():
        p = sub.add_parser(entry.name, help=entry.help or "")
        # 所有子命令都能接收剩余参数，透传给命令处理函数（ctx.args）
        p.add_argument("args", nargs="*", help="命令参数")
        if entry.name == "login":
            p.add_argument("--url", default=None,
                           help="服务端地址，覆盖会话/环境变量配置")
        builtin_names.add(entry.name)

    # 远程命令（服务端提供），仅在已登录时注册为子命令
    if ctx.session:
        remote_cmds = _load_remote_commands(ctx)
        for name in sorted(remote_cmds.keys()):
            if name in builtin_names:
                continue
            rp = sub.add_parser(name, help=remote_cmds.get(name, ""))
            rp.add_argument("args", nargs="*", help="传递给服务端命令的参数")

    return parser


def main(argv=None):    # type: (Optional[List[str]]) -> int
    if argv is None:
        argv = sys.argv[1:]
    _ensure_registered()

    # 先构建 argparse 解析器（子命令含本地命令 + 已登录时的远程命令）
    help_ctx = XnoteCliContext()
    help_ctx.session = load_session()
    parser = _build_parser(help_ctx)

    args = parser.parse_args(argv)

    if not getattr(args, "command", None):
        # 无子命令：打印帮助（argparse 在 -h 时已经自行打印并退出）
        _print_help()
        return 0

    name = args.command  # type: str

    # 本地命令（在客户端进程注册的命令）
    if name in COMMANDS:
        entry = COMMANDS[name]
        ctx = XnoteCliContext(command=name, args=list(getattr(args, "args", [])))
        ctx.session = help_ctx.session
        ctx.server_url = get_server_url(ctx)
        if name == "login" and getattr(args, "url", None):
            # login --url 覆盖服务端地址（复用环境变量逻辑）
            os.environ["XNOTE_CLI_URL"] = args.url
            ctx.server_url = get_server_url(ctx)
        try:
            return entry.handler(ctx) or 0
        except XnoteCliError as e:
            print(str(e))
            return 1
        except Exception as e:
            print("命令执行失败：%s" % e)
            return 1

    # 远程命令（服务端插件提供，登录后从 /api/cli/command_list 获取）
    remote_cmds = _load_remote_commands(help_ctx)
    if name in remote_cmds:
        ctx = XnoteCliContext(command=name, args=list(getattr(args, "args", [])))
        ctx.session = help_ctx.session
        ctx.server_url = get_server_url(ctx)
        return _forward_to_server(ctx, name, ctx.args)

    # 兜底：理论上 argparse 已对未知子命令报错退出，这里仅作为安全网
    print("未知命令: %s" % name)
    _print_help()
    return 1


def _ensure_registered():
    # type: () -> None
    global _registered
    if _registered:
        return
    _registered = True
    from xnote_cli import commands
    commands.register_builtin_commands()
