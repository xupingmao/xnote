# encoding=utf-8
import web
import os
import xutils

class handler:

    command_list = {
        "open_xnote_dir": "explorer .",
        "shutdown": "shutdown /s /t 60",
    }
    def GET(self):
        args = web.input()
        path = args.path
        command = xutils.readfile(path)
        os.popen(command)
        return "<script>window.close()</script>"