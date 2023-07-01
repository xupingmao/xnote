# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-03 22:43:20
@LastEditors  : xupingmao
@LastEditTime : 2023-07-01 18:29:41
@FilePath     : /xnote/handlers/system/db_refresh.py
@Description  : 数据库定时任务
"""

import xauth
from xutils import dbutil
from xutils import cacheutil
from xutils.db import dbutil_cache
from xutils.db.binlog import BinLog

class RefreshHandler:

    @xauth.login_required("admin")
    def GET(self):
        result = []
        for table_info in dbutil.get_table_dict_copy().values():
            count = dbutil.count_table(table_info.name)
            result.append((table_info.name, count))
        
        db_cache = dbutil_cache.DatabaseCache()
        db_cache.clear_expired()

        cacheutil._global_cache.clear_expired()
        BinLog.get_instance().delete_expired()
        
        return result


xurls = (
    r"/system/db_refresh", RefreshHandler,
)
