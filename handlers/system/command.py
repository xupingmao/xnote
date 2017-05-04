# encoding=utf-8
import web
import os
import xutils
import subprocess
import xauth

class handler:

    command_list = {
        "open_xnote_dir": "explorer .",
        "shutdown": "shutdown /s /t 60",
    }

    @xauth.login_required("admin")
    def GET(self):
        args = web.input()
        path = args.path
        # command = xutils.readfile(path)
        # subprocess和os.popen不能执行多条命令(win32)
        # subprocess在IDLE下会创建新的会话窗口，cmd下也不会创建新窗口
        # subprocess执行命令不能换行
        # os.popen可以执行系统命令
        # os.popen就是subprocess.Popen的封装
        print(path)
        if path.endswith(".bat"):
            os.popen("start %s" % path)
        else:
            os.popen(path)
        # os.popen(command)
        return "success"

    @xauth.login_required("admin")
    def POST(self):
        input_str = web.data().decode("utf-8")
        # input_str = web.data()
        return os.popen(input_str).read()
