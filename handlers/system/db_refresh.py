# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-03 22:43:20
@LastEditors  : xupingmao
@LastEditTime : 2022-05-03 23:09:00
@FilePath     : /xnote/handlers/system/db_refresh.py
@Description  : 数据库定时任务
"""

import xauth
from xutils import dbutil

class RefreshHandler:

    @xauth.login_required("admin")
    def GET(self):
        result = []
        for table_name in dbutil.get_table_names():
            count = dbutil.count_table(table_name)
            result.append((table_name, count))
        return result


xurls = (
    r"/system/db_refresh", RefreshHandler,
)
