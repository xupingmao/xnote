# encoding=utf-8

"""哨兵进程

错误码说明

错误码 | 说明
------| -------
0     | 正常退出
1     | 异常退出，一般是程序错误

https://blog.csdn.net/halfclear/article/details/72783900

"""

import sys
import os
import time

def get_current_time(format='%Y-%m-%d %H:%M:%S'):
	return time.strftime(format)

def print_log(*args):
	print(get_current_time(), *args)

def main():
	args = sys.argv[1:]
	args.insert(0, sys.executable)
	cmd = " ".join(args)
	print_log("command:", cmd)
	while True:
		# exit_code = subprocess.call(args, shell = True)
		exit_code = os.system(cmd)
		print_log("exit_code:", exit_code)
		# Mac返回 52480
		if exit_code in (205, 52480):
			print_log("restart ...")
			print_log("-" * 50)
			print_log("-" * 50)
		else:
			return


if __name__ == '__main__':
	main()