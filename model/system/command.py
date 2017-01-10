# encoding=utf-8
import web
import os
import xutils
import subprocess

class handler:

    command_list = {
        "open_xnote_dir": "explorer .",
        "shutdown": "shutdown /s /t 60",
    }
    def GET(self):
        args = web.input()
        path = args.path
        # command = xutils.readfile(path)
        # subprocess和os.popen不能执行多条命令(win32)
        # subprocess在IDLE下会创建新的会话窗口，cmd下也不会创建新窗口
        # subprocess执行命令不能换行
        # os.popen可以执行系统命令
        # os.popen就是subprocess.Popen的封装
        os.popen("start %s" % path)
        # os.popen(command)
        return "<script>window.close()</script>"