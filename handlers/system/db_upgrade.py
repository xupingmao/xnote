# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/31 23:06:44
# @modified 2022/02/20 23:03:42
# @filename upgrade_main.py

"""系统升级相关的自动化脚本

使用约定:
1. 升级文件名为`handlers/upgrade/upgrade_03d%.py`
    文件名按数字递增，执行顺序按数字顺序
    可以跳过某些数字
2. 升级文件中的入口为`do_upgrade`
3. 升级文件需要自己处理幂等逻辑，这里提供了幂等表`upgrade_log`
"""
import xutils
import xauth
import xnote_migrate
from xutils import dateutil, dbutil
from xutils import Storage

sys_log_db = dbutil.get_table("sys_log")

class UpgradeHandler:

    @xauth.login_required("admin")
    def GET(self):
        try:
            xnote_migrate.migrate()
            return "success"
        except:
            err_msg = xutils.print_exc()
            
            err_log = Storage()
            err_log.time = dateutil.format_datetime()
            err_log.msg = err_msg
            err_log.level = "ERROR"
            err_log.biz_type = "upgrade"

            sys_log_db.insert(err_log)


xurls = (
    r"/upgrade/main", UpgradeHandler
)
