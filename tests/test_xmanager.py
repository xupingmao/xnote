# encoding=utf-8
import sys
import time
import unittest
sys.path.insert(1, "lib")

from xutils   import Storage
from xmanager import TaskManager

class TestMain(unittest.TestCase):

    def test_match(self):
        task_manager = TaskManager(None)

        tm = time.localtime()

        task = Storage()
        task.tm_wday = "*"
        task.tm_hour = "*"
        task.tm_min  = "*"
        r = task_manager.match(task, tm)
        self.assertEqual(True, r)
