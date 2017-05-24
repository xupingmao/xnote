# encoding=utf-8
import sys
sys.path.insert(1, "lib")

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

    def test_fs(self):
        import handlers.fs.fs as fs
        item0, item1 = fs.getpathlist("/fs/test/")
        self.assertEqual("/fs/", item0.path)
        self.assertEqual("/fs/test/", item1.path)

        item0, item1, item2 = fs.getpathlist("C:/data/name/")
        self.assertEqual("C:/", item0.path)
        self.assertEqual("C:/data/", item1.path)
        self.assertEqual("C:/data/name/", item2.path)





