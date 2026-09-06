# -*- coding: utf-8 -*-
"""示例插件：演示如何通过 register_cmd 在服务端动态注册 cli 命令

该命令注册后，CLI 可以执行：xnote-cli hello <name>
CLI 会把命令转发到服务端的 /api/cli/run 接口执行本处理函数。
"""
import xnote_cli
from xnote_cli import XnoteCliContext


def hello_handler(ctx):
    # type: (XnoteCliContext) -> str
    return "hello " + " ".join(ctx.args)


xnote_cli.register_cmd("hello", hello_handler, "服务端插件示例：返回 hello <参数>")
