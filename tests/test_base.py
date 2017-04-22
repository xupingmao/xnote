# encoding=utf-8
import time
import unittest

from handlers.base import *

date = time.strftime("%Y/%m")

class TestMain(unittest.TestCase):

    def test_get_upload_file_path(self):
        path, webpath = get_upload_file_path("test.txt")
        print()
        print(path)
        print(webpath)
        self.assertEqual(config.DATA_PATH + "/files/%s/test.txt" % date, path)
        self.assertEqual("/data/files/%s/test.txt" % date, webpath)

    def test_get_upload_file_path_1(self):
        path, webpath = get_upload_file_path("test.txt", _test_exists=1)
        print()
        print(path)
        print(webpath)
        self.assertEqual(config.DATA_PATH + "/files/%s/test_1.txt" % date, path)
        self.assertEqual("/data/files/%s/test_1.txt" % date, webpath)

    def test_get_upload_file_path_2(self):
        path, webpath = get_upload_file_path("test.txt", _test_exists=2)
        print()
        print(path)
        print(webpath)
        self.assertEqual(config.DATA_PATH + "/files/%s/test_2.txt" % date, path)
        self.assertEqual("/data/files/%s/test_2.txt" % date, webpath)

    def test_get_upload_img_path(self):
        path, webpath = get_upload_img_path("abc.png")
        print()
        print(path)
        print(webpath)
        self.assertEqual(config.DATA_PATH + "/img/%s/abc.png" % date, path)
        self.assertEqual("/data/img/%s/abc.png" % date, webpath)
