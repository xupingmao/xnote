# -*- coding:utf-8 -*-
# @author mark
# @since 2022/02/27 22:55:39
# @modified 2022/04/10 21:47:55
# @filename fs_cache.py

"""TODO: 功能开发中"""

import xutils
import web

class CacheHandler:

	def GET(self):
		url = xutils.get_argument("url")
		if url == "" or url == None:
			return dict(code = "fail")

		# TODO 缓存数据
		# 需要考虑安全性问题，最好是根据白名单缓存
		url = xutils.urlsafe_b64decode(url)
		print("URL:", url)
		raise web.notfound()

xurls = (
	r"/fs/cache", CacheHandler
)