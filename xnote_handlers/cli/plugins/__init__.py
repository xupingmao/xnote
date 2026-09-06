# -*- coding: utf-8 -*-
"""xnote-cli 服务端插件目录

插件是普通的 Python 模块，在被导入时会主动调用 xnote_cli.register_cmd
动态注册服务端命令。CLI 通过 /api/cli/run 接口把命令转发到服务端执行。

本目录下的模块由服务端的模块自动发现机制（xmanager.load_model_dir
递归导入 xnote_handlers 下的所有 .py 模块）在导入时自动注册，无需
在核心代码里手动遍历加载。新增插件：在本目录下新建一个 .py 文件，在其中
import xnote_cli 并调用 xnote_cli.register_cmd 即可。
"""
