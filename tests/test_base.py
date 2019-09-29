# encoding=utf-8
import sys
sys.path.insert(1, "lib")
import os
import time
import unittest
import xconfig
import xutils
from xutils import get_upload_file_path

config = xconfig
date = time.strftime("%Y/%m")

def create_tmp_file(name):
    path = os.path.join(xconfig.DATA_DIR, "files", "user", "upload", time.strftime("%Y/%m"), name)
    xutils.touch(path)

def remove_tmp_file(name):
    path = os.path.join(xconfig.DATA_DIR, "files", "user", "upload", time.strftime("%Y/%m"), name)
    if os.path.exists(path):
        os.remove(path)

class TestMain(unittest.TestCase):

    def test_get_upload_file_path(self):
        remove_tmp_file("test.txt")
        path, webpath = get_upload_file_path("user", "test.txt")
        print()
        print(path)
        print(webpath)
        self.assertEqual(os.path.abspath(config.DATA_PATH + "/files/user/upload/%s/test.txt" % date), path)
        self.assertEqual("/data/files/user/upload/%s/test.txt" % date, webpath)

    def test_get_upload_file_path_1(self):
        remove_tmp_file("test_1.txt")
        create_tmp_file("test.txt")
        path, webpath = get_upload_file_path("user", "test.txt")
        print()
        print(path)
        print(webpath)
        self.assertEqual(os.path.abspath(config.DATA_PATH + "/files/user/upload/%s/test_1.txt" % date), path)
        self.assertEqual("/data/files/user/upload/%s/test_1.txt" % date, webpath)
        remove_tmp_file("test.txt")

    def test_get_upload_file_path_2(self):
        create_tmp_file("test.txt")
        create_tmp_file("test_1.txt")
        remove_tmp_file("test_2.txt")
        path, webpath = get_upload_file_path("user", "test.txt")
        print()
        print(path)
        print(webpath)
        self.assertEqual(os.path.abspath(config.DATA_PATH + "/files/user/upload/%s/test_2.txt" % date), path)
        self.assertEqual("/data/files/user/upload/%s/test_2.txt" % date, webpath)
        remove_tmp_file("test.txt")
        remove_tmp_file("test_1.txt")

