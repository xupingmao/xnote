# encoding=utf-8
import os
import sys
sys.path.insert(1, "lib")
import unittest

# class test_1(unittest.TestCase):

#     def test_1(self):
#         print("hello")
#         self.assertEqual(0, 0)

def run_test(path = "tests"):
    for file in os.listdir(path):
        if file.endswith(".py"):
            print("run", file)
            basename, ext = os.path.splitext(file)
            mod = __import__("tests."+basename, fromlist=1,level=0)
            suite = unittest.TestLoader().loadTestsFromTestCase(mod.TestMain)
            unittest.TextTestRunner(verbosity=2).run(suite)
            
if __name__ == "__main__":
    run_test()
    # unittest.main()