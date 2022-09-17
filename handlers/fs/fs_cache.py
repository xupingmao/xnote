# -*- coding:utf-8 -*-
# @author mark
# @since 2022/02/27 22:55:39
# @modified 2022/04/10 21:47:55
# @filename fs_cache.py

"""TODO: 功能开发中
网络资源缓存
"""

import web
import os
import xutils
import xconfig
from urllib.parse import urlparse
from xutils import netutil
from xutils import dbutil
from .fs import FileSystemHandler

_ct_db = dbutil.get_hash_table("fs_ctype")

class ImageCacheHandler:
	"""图片缓存处理"""

	def GET(self):
		return dict(code = "500", message="暂不支持")

		url = xutils.get_argument("url")
		if url == "" or url == None:
			return dict(code = "fail")
		
		# TODO 缓存数据
		# 需要考虑安全性问题，最好是根据白名单缓存
		# 1. host不能是内网地址
		# 2. 防止缓存数据过大拖垮服务器
		url = url.replace("\r", "")
		url = url.replace("\n", "")

		host = netutil.get_host_by_url(url)
		# TODO 制作host白名单
		cache_dir = xconfig.get_system_dir("cache")
		
		url_info = urlparse(url)
		url_path = url_info.path.lstrip("/")
		filename = url_path

		if url_info.query != "":
			filename += "_" + url_info.query

		filename = filename.replace("?", "_")
		filename = filename.replace("&", "_")
		filename = filename.replace("/", "_")

		content_type = _ct_db.get(url)
		destpath = os.path.join(cache_dir, host, filename)

		if os.path.exists(destpath) and content_type != None:
			# TODO 注意越权问题 host不能是内部地址
			fs_handler = FileSystemHandler()
			yield from fs_handler.handle_get(destpath, content_type=content_type)
			return 
		
		xutils.makedirs(os.path.join(cache_dir, host))
		resp_headers = netutil.http_download(url, destpath=destpath)
		if resp_headers != None:
			_ct_db.put(url, resp_headers.get("Content-Type"))

		web.ctx.status = "302 Found"
		web.header("Location", url)
		return

xurls = (
	r"/fs_cache/image", ImageCacheHandler
)