# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-03 22:43:20
@LastEditors  : xupingmao
@LastEditTime : 2022-08-14 17:39:01
@FilePath     : /xnote/handlers/system/db_refresh.py
@Description  : 数据库定时任务
"""

import xauth
from xutils import dbutil

class RefreshHandler:

    @xauth.login_required("admin")
    def GET(self):
        result = []
        for table_info in dbutil.get_table_dict_copy().values():
            count = dbutil.count_table(table_info.name)
            result.append((table_info.name, count))
        return result


xurls = (
    r"/system/db_refresh", RefreshHandler,
)
