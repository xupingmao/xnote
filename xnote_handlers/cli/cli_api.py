# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2026/09/05
# @modified 2026/09/05
"""xnote-cli 相关的服务端接口
CLI 的核心逻辑在 xnote_cli 模块下，本模块只负责提供 HTTP 接口，
处理具体的业务逻辑（登录态、备份、修复、同步等）。
"""
import web
import json
import xutils
from typing import Dict, Any

import xnote_cli
from xnote_cli import XnoteCliContext
from xnote.core import xauth
from xutils import webutil, dbutil
from xnote_handlers.user.login import LoginHandler
from xnote_handlers.system.backup import chk_db_backup


def _get_login_sid(user_name):
    # type: (str) -> str
    """获取该用户最近一次登录创建的会话 sid

    服务端登录会创建会话并（在生产环境）通过 Set-Cookie 下发，
    但测试环境不会下发 Cookie，因此这里直接从会话存储取最新的 sid 回传。
    """
    sessions = xauth.list_user_session_detail(user_name)
    if not sessions:
        return ""
    sessions.sort(key=lambda s: s.expire_time, reverse=True)
    return sessions[0].sid


class LoginApiHandler:

    def POST(self):
        # 兼容 JSON 体和表单两种提交方式
        name = ""
        pswd = ""
        try:
            request_data = str(web.data(), "UTF-8")
            if request_data:
                request_json = json.loads(request_data)
                name = request_json.get("username", "")
                pswd = request_json.get("password", "")
        except Exception:
            pass
        if name == "" or pswd == "":
            name = xutils.get_argument_str("username", "")
            pswd = xutils.get_argument_str("password", "")

        handler = LoginHandler()
        error = handler.do_login_with_error(name, pswd)
        if error == "":
            # 返回会话 sid，客户端据此构造 Cookie 头（测试环境不下发 Set-Cookie，
            # 故通过响应体回传，兼容性更好）
            return webutil.SuccessResult(data=dict(name=name, sid=_get_login_sid(name)))
        return webutil.FailedResult(code="login_failed", message=error)


class LogoutApiHandler:

    @xauth.login_required()
    def POST(self):
        xauth.logout_current_user()
        web.setcookie("sid", "", expires=-1)
        return webutil.SuccessResult()


class BackupApiHandler:

    @xauth.login_required("admin")
    def POST(self):
        result = chk_db_backup()
        if result == "skip":
            return webutil.FailedResult(code="skip", message="备份未开启")
        return webutil.SuccessResult(data=dict(result=result))


class RepairApiHandler:

    @xauth.login_required("admin")
    def POST(self):
        # TODO: 暂未实现，保留接口占位
        return webutil.SuccessResult(data="repair 功能暂未实现")


class SyncApiHandler:

    @xauth.login_required("admin")
    def POST(self):
        # TODO: 暂未实现，保留接口占位
        return webutil.SuccessResult(data="sync 功能暂未实现")


class CommandListApiHandler:

    @xauth.login_required()
    def GET(self):
        # 列出服务端动态注册的命令（插件命令）
        result = []
        for name in sorted(xnote_cli.COMMANDS.keys()):
            entry = xnote_cli.COMMANDS[name]
            result.append(dict(name=name, help=entry.help))
        return webutil.SuccessResult(data=result)


class RunApiHandler:

    @xauth.login_required()
    def POST(self):
        # 在服务端执行插件命令
        cmd = xutils.get_argument_str("cmd", "")
        args_str = xutils.get_argument_str("args", "")
        args = args_str.split("\n") if args_str else []

        entry = xnote_cli.get_command(cmd)
        if entry is None:
            return webutil.FailedResult(code="not_found", message="命令不存在: %s" % cmd)

        ctx = XnoteCliContext(command=cmd, args=args)
        try:
            output = entry.handler(ctx)
        except xnote_cli.XnoteCliError as e:
            return webutil.FailedResult(code="cli_error", message=str(e))
        if output is None:
            output = ""
        if isinstance(output, (dict, list)):
            return webutil.SuccessResult(data=output)
        return webutil.SuccessResult(data=str(output))


xurls = (
    r"/api/cli/login", LoginApiHandler,
    r"/api/cli/logout", LogoutApiHandler,
    r"/api/cli/backup", BackupApiHandler,
    r"/api/cli/repair", RepairApiHandler,
    r"/api/cli/sync", SyncApiHandler,
    r"/api/cli/command_list", CommandListApiHandler,
    r"/api/cli/run", RunApiHandler,
)
