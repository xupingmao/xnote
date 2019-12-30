# encoding=utf-8
# @author xupingmao
# @modified 2019/12/30 00:12:25

import web
import os
import xutils
import subprocess
import xauth
import sys

class OpenHandler:
    @xauth.login_required("admin")
    def GET(self):
        path = xutils.get_argument("path")
        path = '"%s"' % path
        if xutils.is_windows():
            path = path.replace("/", "\\")
            cmd = "explorer %s" % path
        elif xutils.is_mac():
            cmd = "open %s" % path
        print(cmd)
        os.popen(cmd)
        return "<html><script>window.close()</script></html>"

    def POST(self):
        return self.GET()

class OpenTerminalHandler:

    @xauth.login_required("admin")
    def POST(self):
        path = xutils.get_argument("path", "")
        # command = xutils.readfile(path)
        # subprocess和os.popen不能执行多条命令(win32)
        # subprocess在IDLE下会创建新的会话窗口，cmd下也不会创建新窗口
        # subprocess执行命令不能换行
        # os.popen可以执行系统命令
        # os.popen就是subprocess.Popen的封装
        if xutils.is_mac():
            os.system("open -a Terminal \"%s\"" % path)
            return "success"
        if xutils.is_windows():
            os.popen("start; cd \"%s\"" % path)
            return "success"
        return "failed"

    def GET(self):
        return self.POST()

class CommandHandler:

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
                os.system("open -a Terminal \"%s\"" % path)
                return "success"
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
        p = None
        try:
            p = subprocess.Popen(input_str, 
                                 shell=True, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
            out = p.stdout.read()
            err = p.stderr.read()
            yield out or b''
            yield err or b''
        except:
            xutils.print_exc()
        finally:
            if p:
                p.stdout.close()
                p.stderr.close()
            yield b''

class PythonCommandHandler:

    @xauth.login_required("admin")
    def POST(self):
        content = xutils.get_argument("content")
        result = xutils.exec_python_code("<shell>", content)
        return dict(code="success", message="", data=result)

xurls = (
    r"/system/command", CommandHandler,
    r"/system/command/open", OpenHandler,
    r"/system/command/openTerminal", OpenTerminalHandler,
    r"/system/command/python", PythonCommandHandler,
)
