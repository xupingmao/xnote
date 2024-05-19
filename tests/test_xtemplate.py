# encoding=utf-8
import unittest
from . import test_base
from xnote.core import xtemplate

app = test_base.init()

class TestMain(unittest.TestCase):

    def test_memory_template(self):
        TEMPLATE_HTML = """hello, {{name}}"""
        xtemplate.register_memory_template("memory:test.simple", TEMPLATE_HTML)
        value = xtemplate.render_text("{% include memory:test.simple %}", name="world")
        assert value == b"hello, world"
