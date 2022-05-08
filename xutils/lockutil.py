# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/04 15:35:23
# @modified 2022/01/23 23:57:56
# @filename lockutil.py
import os
import xutils

try:
	import fcntl
except ImportError:
	fcntl = None

class UnixLock:
	"""Unix环境的锁实现"""

	def __init__(self, fpath):
		self.fpath = fpath
		self.fp = open(fpath, "w+")
		self.got_lock = False

	def try_lock(self):
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

	def unlock(self):
		if self.got_lock:
			fcntl.flock(self.fp, fcntl.LOCK_UN)
			# 不需要重置为空
			self.fp.close()
			self.got_lock = False
		return True

class WinLock:

	def __init__(self, fpath):
		self.fpath = fpath

	def try_lock(self):
		return True

	def unlock(self):
		pass

class WinLockOld:
	"""Windows环境的锁实现"""

	def __init__(self, fpath):
		self.fpath = fpath
		self.got_lock = False

		if not os.path.exists(self.fpath):
			self.got_lock = True
			self.fp = open(fpath, "w+")
			return

		self.fp = open(fpath)

	def do_get_lock(self):
		# 关闭读，重新打开为写模式
		self.fp.close()
		self.fp = open(self.fpath, "w+")
		self.fp.write(str(os.getpid()))
		self.fp.flush()
		self.got_lock = True

	def try_lock(self):
		data = self.fp.read(1024)
		if data == str(os.getpid()) or data == "":
			self.do_get_lock()
			return True

		return False

	def unlock(self):
		if self.got_lock:
			self.fp.write("")
			self.got_lock = False

		if self.fp != None:
			self.fp.close()
			self.fp = None


class FileLock:
	"""文件锁，注意目前只支持posix系统"""

	def __init__(self, fpath):
		if fcntl != None:
			self.impl = UnixLock(fpath)
		else:
			self.impl = WinLock(fpath)

	def acquire(self):
		return self.impl.try_lock()

	def release(self):
		return self.impl.unlock()


