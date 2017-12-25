# encoding=utf-8
import sys
import os
sys.path.insert(1, "lib")

import unittest
import xutils

@xutils.cache(prefix='fib')
def fib(n):
    if n == 1 or n == 2:
        return 1
    return fib(n-1) + fib(n-2)

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

    def test_get_opt(self):
        # 不好用
        import getopt
        opts, args = getopt.getopt(["--data","/data", "--log", "/log/log.log"], "x", ["data=", "log="])
        print()
        print(opts)
        print(args)
        self.assertEqual(opts[0], ("--data", "/data"))

    def test_argparse(self):
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("-a", action="store", default=False)
        parser.add_argument("--data", default="./data")
        parser.add_argument("--test", default=True)
        result = parser.parse_args(["-a", "1", "--data", "/data"])
        print()
        print(result)
        self.assertEqual(True, hasattr(result, "data"))
        self.assertEqual(False, hasattr(result, "not_exists"))
        self.assertEqual("1", result.a)
        self.assertEqual("/data", result.data)
        self.assertEqual(True, result.test)

    def test_get_relative_path(self):
        path   = "./test/test.html"
        parent = "./"
        relative_path = xutils.get_relative_path(path, parent)
        self.assertEqual("test/test.html", relative_path)

        path   = "./test.html"
        parent = "./"
        relative_path = xutils.get_relative_path(path, parent)
        self.assertEqual("test.html", relative_path)

        path = "./test/test.html"
        parent = "./test"
        relative_path = xutils.get_relative_path(path, parent)
        self.assertEqual("test.html", relative_path)

    def test_splitpath(self):
        path = "/root/test"
        pathlist = xutils.splitpath(path)
        self.assertEqual(2, len(pathlist))

    def test_decode_name(self):
        self.assertEqual("a.txt", xutils.decode_name("a.txt"))
        self.assertEqual("a.txt", xutils.decode_name("YS50eHQ=.x0"))
        self.assertEqual("a.txt", xutils.decode_name("YS50eHQ=.xenc"))

    def test_encode_name(self):
        self.assertEqual("YS50eHQ=.x0", xutils.encode_name("a.txt"))
        self.assertEqual("YS50eHQ=.x0", xutils.encode_name("YS50eHQ=.x0"))

    def test_edit_distance(self):
        self.assertEqual(1, xutils.edit_distance("abcd","abc"))
        self.assertEqual(2, xutils.edit_distance("abcd", "ab"))
        self.assertEqual(3, xutils.edit_distance("abc", "def"))
        self.assertEqual(3, xutils.edit_distance("kkabcd", "abc"))

    def test_bs4(self):
        html = "<p>hello<p><p>world</p>"
        if xutils.bs4 is not None:
            soup = xutils.bs4.BeautifulSoup(html, "html.parser")
            text = soup.get_text(separator=" ")
            self.assertEqual("hello world", text)


    def test_search_path(self):
        print(os.getcwd())
        result = xutils.search_path("./", "*test*")
        self.assertTrue(len(result) > 0)

    def test_cache(self):
        fib(35)
        self.assertTrue(xutils.expire_cache("fib(1,)"))


        
