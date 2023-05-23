# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-09-12 20:41:26
@LastEditors  : xupingmao
@LastEditTime : 2023-05-21 21:46:00
@FilePath     : /xnote/handlers/system/cache_admin.py
@Description  : 缓存管理
"""
import xauth
import xtemplate
import sys
from xutils import Storage
from xutils import cacheutil
from xutils import dateutil
import xutils

class CacheHandler:

    @xauth.login_required("admin")
    def GET(self):
        page = xutils.get_argument("page", 1)
        limit = xutils.get_argument("page_size", 20)
        
        offset = (page-1) * limit
        kw = Storage()
        cache_size = 0
        cache_list = []
        cache = cacheutil.get_global_cache()

        # 按照缓存的访问顺序排列，最近访问的在前面
        keys = list(cache.keys())
        
        for key in keys:
            value = cache.get_raw(key)
            cache_size += sys.getsizeof(value)

        key_page = keys[offset:offset+limit]

        for key in key_page:
            expire_time = cache.get_expire(key)
            expire_text = dateutil.format_time(expire_time)
            value = cache.get_raw(key)
            if isinstance(value, bytes):
                value = str(value)
            value_short = value
            if value != None and len(value) > 50:
                value_short = value[:50] + "..."

            item = Storage(key=key, value=value, value_short=value_short, expire=expire_text)
            cache_list.append(item)

        kw.cache_list = cache_list
        kw.cache_count = len(keys)
        kw.cache_size = xutils.format_size(cache_size)
        kw.page_totalsize = len(keys)
        kw.page_size = limit

        return xtemplate.render("system/page/cache_admin.html", **kw)

    @xauth.login_required("admin")
    def POST(self):
        pass


class CacheAjaxHandler:

    @xauth.login_required("admin")
    def POST(self):
        key = xutils.get_argument("key", "")
        value = xutils.get_argument("value", "")
        cacheutil.put(key, value)
        return dict(code = "success")

    @xauth.login_required("admin")
    def GET(self):
        key = xutils.get_argument("key", "")
        return dict(code = "success", data = cacheutil.get(key))


xurls = (
    r"/system/cache", CacheHandler,
    r"/system/cache/detail", CacheAjaxHandler,
)