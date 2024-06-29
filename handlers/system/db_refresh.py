# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-03 22:43:20
@LastEditors  : xupingmao
@LastEditTime : 2024-06-26 00:57:39
@FilePath     : /xnote/handlers/system/db_refresh.py
@Description  : 数据库定时任务
"""
from xnote.core import xauth
from xnote.core import xconfig
from xutils import dbutil
from xutils import cacheutil
from xutils.db import dbutil_cache
from xutils.db.binlog import BinLog
from xnote.service import DatabaseLockService


class RefreshHandler:

    sys_log_db = dbutil.get_table("sys_log")
    sys_log_db.binlog_enabled = False
    
    @xauth.login_required("admin")
    def GET(self):
        result = []
        for table_info in dbutil.get_table_dict_copy().values():
            count = dbutil.count_table(table_info.name, use_cache=True)
            result.append((table_info.name, count))
        
        db_cache = dbutil_cache.DatabaseCache()
        db_cache.clear_expired()

        # 清理失效的缓存
        cacheutil._global_cache.clear_expired()
        BinLog.get_instance().delete_expired()
        
        # 清理sys_log
        self.delete_expired_sys_log()

        return result

    def delete_expired_sys_log(self):
        # TODO 优化到log模块
        lock_key = "del_sys_log"
        with DatabaseLockService.lock(lock_key=lock_key, timeout_seconds=600):
            count = dbutil.count_table(self.sys_log_db.table_name)
            if count > xconfig.DatabaseConfig.db_sys_log_max_size:
                delete_count = count - xconfig.DatabaseConfig.db_sys_log_max_size
                for obj in self.sys_log_db.iter(limit=delete_count):
                    self.sys_log_db.delete(obj)

xurls = (
    r"/system/db_refresh", RefreshHandler,
)
