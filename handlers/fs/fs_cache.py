# -*- coding:utf-8 -*-
# @author mark
# @since 2022/02/27 22:55:39
# @modified 2022/03/12 10:43:35
# @filename fs_cache.py

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