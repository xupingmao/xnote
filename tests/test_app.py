# encoding=utf-8

import unittest
import json
import web

import xmanager
import xutils
import xtemplate
import config
import xtables

def init():
    xtables.init()
    config.IS_TEST = True
    var_env = dict()
    app = web.application(list(), var_env, autoreload=False)
    mgr = xmanager.init(app, var_env)
    mgr.reload()
    return app

app = init()

class TestMain(unittest.TestCase):

    def test_render_text(self):
        value = xtemplate.render_text("Hello,{{name}}", name="World")
        self.assertEqual(b"Hello,World", value)

    def test_render(self):
        value = app.request("/test").data
        self.assertEqual(b"success", value)

    def test_recent_files(self):
        value = app.request("/file/recent_edit?_type=json").data
        json_value = value.decode("utf-8")
        files = json.loads(json_value)["files"]
        print("files=%s" % len(files))

