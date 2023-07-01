# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-09-12 20:41:26
@LastEditors  : xupingmao
@LastEditTime : 2023-07-01 10:53:48
@FilePath     : /xnote/handlers/system/cache_admin.py
@Description  : 缓存管理
"""
import xauth
import xtemplate
import sys
from xutils import Storage
from xutils import cacheutil
from xutils import dateutil
from xutils import dbutil
import xutils

class CacheHandler:

    @xauth.login_required("admin")
    def GET(self):
        page = xutils.get_argument_int("page", 1)
        limit = xutils.get_argument_int("page_size", 20)
        type = xutils.get_argument_str("type")

        offset = (page-1) * limit
        kw = Storage()
        cache_size = 0
        cache_list = []

        if type == "db":
            cache = cacheutil.DatabaseCache()
            key_page = cache.list_keys(offset=offset, limit=limit)
            total = dbutil.count_table(cache.prefix)
            cache_size = -1
        else:
            cache = cacheutil.get_global_cache()
            # 按照缓存的访问顺序排列，最近访问的在前面
            keys = cache.keys()
        
            for key in keys:
                value = cache.get_raw(key)
                cache_size += sys.getsizeof(value)

            key_page = keys[offset:offset+limit]
            total = len(keys)

        for key in key_page:
            expire_time = cache.get_expire(key)
            expire_text = dateutil.format_time(expire_time)
            value = cache.get(key)
            if isinstance(value, bytes):
                value = str(value)
            value_short = value
            if isinstance(value, str) and len(value) > 50:
                value_short = value[:50] + "..."

            item = Storage(key=key, value=value, value_short=value_short, expire=expire_text)
            cache_list.append(item)

        kw.cache_list = cache_list
        kw.cache_count = total
        kw.cache_size = xutils.format_size(cache_size)
        kw.page_totalsize = total
        kw.page_size = limit
        kw.page_url = "?type=%s&page=" % type

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