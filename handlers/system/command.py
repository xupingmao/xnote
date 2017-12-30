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
        command = xutils.get_argument("command", "")
        path    = xutils.get_argument("path", "")
        # command = xutils.readfile(path)
        # subprocess和os.popen不能执行多条命令(win32)
        # subprocess在IDLE下会创建新的会话窗口，cmd下也不会创建新窗口
        # subprocess执行命令不能换行
        # os.popen可以执行系统命令
        # os.popen就是subprocess.Popen的封装
        print(command, path)
        if command == "openTerminal":
            if xutils.is_mac():
                # TODO
                pass
            if xutils.is_windows():
                os.popen("start; cd \"%s\"" % path)
            return "success"
        if path.endswith(".bat"):
            os.popen("start %s" % path)
        else:
            os.popen(path)
        # os.popen(command)
        return "success"

    @xauth.login_required("admin")
    def POST(self):
        bufsize = 1024
        input_str = xutils.get_argument("command")
        try:
            fp = os.popen(input_str)
            buf = fp.read(bufsize)
            while buf:
                yield buf
                buf = fp.read(bufsize)
        finally:
            fp.close()
