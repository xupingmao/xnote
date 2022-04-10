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
import subprocess

def main():
	args = sys.argv[1:]
	args.insert(0, sys.executable)
	cmd = " ".join(args)
	print("Command", cmd)
	while True:
		# exit_code = subprocess.call(args, shell = True)
		exit_code = os.system(cmd)
		print("exit_code:", exit_code)
		# Mac返回 52480
		if exit_code in (205, 52480):
			print("restart ...")
			print("-" * 50)
			print("-" * 50)
		else:
			return


if __name__ == '__main__':
	main()