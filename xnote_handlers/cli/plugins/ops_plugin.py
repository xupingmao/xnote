# -*- coding: utf-8 -*-
"""运维相关的服务端 CLI 命令（远程命令）

backup 为已实现的命令；repair / sync 暂未实现，仅占位注册，
由 CLI 客户端在登录后从 /api/cli/command_list 获取并转发执行。
"""
import xnote_cli
from xnote_cli import XnoteCliContext, XnoteCliError
from xnote.core import xauth
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


xnote_cli.register_cmd("backup", backup_handler, "备份数据")
xnote_cli.register_cmd("repair", repair_handler, "修复数据（暂未实现）")
xnote_cli.register_cmd("sync", sync_handler, "触发数据同步（暂未实现）")
