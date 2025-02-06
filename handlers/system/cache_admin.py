# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-09-12 20:41:26
@LastEditors  : xupingmao
@LastEditTime : 2024-07-13 02:02:14
@FilePath     : /xnote/handlers/system/cache_admin.py
@Description  : 缓存管理
"""
import sys
import xutils

from xnote.core import xauth
from xnote.core import xtemplate
from xutils import Storage
from xutils import cacheutil
from xutils import dateutil
from xutils import dbutil
from xutils import webutil
from xutils import textutil

from xnote.plugin.table_plugin import BaseTablePlugin

class CacheHandler(BaseTablePlugin):
    title = "缓存信息"
    require_admin = True
    show_aside = True
    show_right = True

    NAV_HTML = """
<div class="card">
    <div class="x-tab-box" data-tab-key="type" data-tab-default="local">
        <a class="x-tab" href="{{_server_home}}/system/cache?type=local" data-tab-value="local">单机缓存</a>
        <a class="x-tab" href="{{_server_home}}/system/cache?type=db" data-tab-value="db">数据库缓存</a>
    </div>
</div>

<div class="card btn-line-height">
    <span>缓存总数: {{cache_count}}</span>
    <span>缓存大小: {{cache_size}}</span>
</div>
"""
    PAGE_HTML = NAV_HTML + BaseTablePlugin.TABLE_HTML

    def get_aside_html(self):
        return xtemplate.render_text("{% include system/component/admin_nav.html %}")

    def handle_page(self):
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

        table = self.create_table()
        table.default_head_style.width = "33.3%"
        table.add_head("Key", field="key")
        table.add_head("Value", field="value_short", detail_field="value")
        table.add_head("Expire", field="expire")

        for key in key_page:
            expire_time = cache.get_expire(key)
            expire_text = dateutil.format_time(expire_time)
            value = textutil.tojson(cache.get(key), format=True)
            value_short = textutil.get_short_text(value, 100)
            row = Storage(key=key, value=value, value_short=value_short, expire=expire_text)
            table.add_row(row)

        kw.cache_list = cache_list
        kw.cache_count = total
        kw.cache_size = xutils.format_size(cache_size)
        kw.page_totalsize = total
        kw.page_size = limit
        kw.page_url = "?type=%s&page=" % type
        kw.table = table

        return self.response_page(**kw)

    @xauth.login_required("admin")
    def POST(self):
        pass


class CacheAjaxHandler:

    @xauth.login_required("admin")
    def POST(self):
        key = xutils.get_argument_str("key", "")
        value = xutils.get_argument_str("value", "")
        cacheutil.put(key, value)
        return webutil.SuccessResult()

    @xauth.login_required("admin")
    def GET(self):
        key = xutils.get_argument_str("key", "")
        return webutil.SuccessResult(data = cacheutil.get(key))


xurls = (
    r"/system/cache", CacheHandler,
    r"/system/cache/detail", CacheAjaxHandler,
)