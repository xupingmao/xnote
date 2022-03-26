# encoding=utf-8

import os
import shutil
import time
import argparse

def do_clean():
	print("一些清理工作...")
	if os.path.exists("testdata"):
		shutil.rmtree("testdata")

def update_version():
	print("更新版本号...")
	version = "v2.8-dev-" + time.strftime("%Y.%m.%d")
	print("版本号:", version)
	with open("config/version.txt", "w+") as fp:
		fp.write(version + "\n")


def check_and_install_pkg(pkg, version = ""):
	try:
		__import__(pkg)
	except ImportError:
		print("准备安装:", pkg, version)
		os.system("python3 -m pip install %s%s" % (pkg, version))

def run_test(target = None):
	os.system("python3 -m pip install pytest==5.1.0")
	os.system("python3 -m pip install pytest-cov==2.7.1")
	os.system("python3 -m pip install python-coveralls==2.9.3")
	os.system("python3 -m pip install coverage==4.5.4")

	if target == "xutils_db":
		os.system("python3 -m pytest tests/test_xutils_db.py --doctest-modules --cov xutils.db")
		os.system("python3 -m coverage html")
	else:
		os.system("python3 -m pytest tests --doctest-modules --cov handlers --cov xutils --cov core")
		os.system("python3 -m coverage html")

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("target", default="all", nargs="?")
	args = parser.parse_args()

	do_clean()

	update_version()

	run_test(args.target)

	# do_clean()

if __name__ == '__main__':
	main()
