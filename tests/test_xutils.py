# encoding=utf-8

import unittest
import xutils

class TestMain(unittest.TestCase):
    def test_quote_unicode(self):
        result = xutils.quote_unicode("http://测试")
        self.assertEqual("http://%E6%B5%8B%E8%AF%95", result)
        result = xutils.quote_unicode("http://test/测试")
        self.assertEqual("http://test/%E6%B5%8B%E8%AF%95", result)

    def test_quote_unicode_2(self):
        result = xutils.quote_unicode("http://test?name=测试")
        self.assertEqual("http://test?name=%E6%B5%8B%E8%AF%95", result)
        result = xutils.quote_unicode("http://test?name=测试&age=10")
        self.assertEqual("http://test?name=%E6%B5%8B%E8%AF%95&age=10", result)

