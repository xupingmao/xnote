# -*- coding: utf-8 -*-
"""运维相关的服务端 CLI 命令（远程命令）

backup 为已实现的命令；repair / sync 暂未实现，仅占位注册，
由 CLI 客户端在登录后从 /api/cli/command_list 获取并转发执行。
"""
import xnote_cli
from xnote_cli import XnoteCliContext, XnoteCliError
from xnote.core import xauth
from xnote.core import xmanager
from xnote_handlers.system.backup import chk_db_backup


def _require_admin():
    # type: () -> None
    if not xauth.is_admin():
        raise XnoteCliError("需要管理员权限")


def backup_handler(ctx):
    # type: (XnoteCliContext) -> object
    _require_admin()
    result = chk_db_backup()
    if result == "skip":
        return "备份未开启"
    return "备份完成: " + str(result)


def repair_handler(ctx):
    # type: (XnoteCliContext) -> object
    # TODO: 暂未实现，保留命令占位以便 command_list 列出
    return "repair 功能暂未实现"


def sync_handler(ctx):
    # type: (XnoteCliContext) -> object
    # TODO: 暂未实现，保留命令占位以便 command_list 列出
    return "sync 功能暂未实现"


def restart_handler(ctx):
    # type: (XnoteCliContext) -> object
    _require_admin()
    # 复用服务端的重启流程：写入重启标记(xnote-reboot.txt)并以 exit(205) 退出，
    # 由哨兵进程(sentinel.py)重新拉起服务。与服务端「重载」按钮(ReloadHandler)同机制。
    # 注意：xmanager.restart() 会直接结束进程，正常情况下不会返回。
    xmanager.restart()
    return "服务正在重启"  # 仅在 xmanager.restart 被 mock 的测试场景下可达


xnote_cli.register_cmd("backup", backup_handler, "备份数据")
xnote_cli.register_cmd("repair", repair_handler, "修复数据（暂未实现）")
xnote_cli.register_cmd("sync", sync_handler, "触发数据同步（暂未实现）")
xnote_cli.register_cmd("restart", restart_handler, "重启 xnote 服务（需管理员）")
