# encoding=utf-8

import sys
import os

def _add_to_sys_path(path):
    if path not in sys.path:
        # insert after working dir
        sys.path.insert(1, path)

def fix():
    tools_dir = os.path.dirname(__file__)
    xnote_root = os.path.dirname(tools_dir)
    lib_dir = os.path.join(xnote_root, "lib")
    lib_dir = os.path.abspath(lib_dir)
    # insert after working dir
    _add_to_sys_path(lib_dir)

fix()

import web

urls = (
    '/(.*)', 'hello'
)
app = web.application(urls, globals())

class hello:
    def GET(self, name):
        if not name:
            name = 'World'
        return 'Hello, ' + name + '!'

if __name__ == "__main__":
    app.run()