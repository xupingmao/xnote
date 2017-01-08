# encoding=utf-8
import web
import os

class handler:

    command_list = {
        "open_xnote_dir": "explorer .",
        "shutdown": "shutdown /s /t 60",
    }
    def GET(self):
        args = web.input()
        name = args.name
        command_list = self.command_list
        if name in command_list:
            os.popen(command_list[name])
        return "<script>window.close()</script>"