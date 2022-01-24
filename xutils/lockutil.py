# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/04 15:35:23
# @modified 2022/01/23 23:57:56
# @filename lockutil.py
import logging
import os
import xutils

try:
	import fcntl
except ImportError:
	fcntl = None


class FileLock:
	"""文件锁，注意目前只支持posix系统"""

	def __init__(self, fpath):
		self.fpath = fpath
		self.fp = open(fpath, "w+")
		self.got_lock = False

	def _posix_lock(self):
		try:
			# 获取锁时flock返回None
			# 未获取锁抛出异常: BlockingIOError: [Errno 11] Resource temporarily unavailable
			fcntl.lockf(self.fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
			content = str(os.getpid())
			self.fp.write(content)
			self.fp.flush()
			self.got_lock = True
			return True
		except:
			xutils.print_exc()
			# TODO 这里读取文件内容为空，并且会清除文件内容，但是cat命令可以正常读取
			# pid = self.fp.read(1024)
			# raise Exception("lock file failed, locked by pid:%s" % pid)
			return False
	
	def _posix_unlock(self):
		if self.got_lock:
			fcntl.flock(self.fp, fcntl.LOCK_UN)
			# 不需要重置为空
		return True

	def _other_lock(self):
		data = self.fp.read(1024)
		if data == str(os.getpid()):
			return True
		if data == "":
			self.fp.write(str(os.getpid()))
			return True

		return False

	def _other_unlock(self):
		if self.got_lock:
			self.fp.write("")

	def acquire(self):
		if fcntl != None:
			return self._posix_lock()
		return self._other_lock()

	def release(self):
		try:
			if fcntl != None:
				return self._posix_unlock()
			return self._other_unlock()
		finally:
			if self.fp:
				self.fp.close()


