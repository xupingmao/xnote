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
import os
import xmanager
import xutils
import xauth
import logging
from xutils import six
from xutils import dateutil
from xutils import Storage
from .base import *

@xmanager.listen("sys.reload")
def check_upgrade(ctx = None):
    logging.info("check_upgrade...")
    dirname = os.path.dirname(__file__)

    for fname in sorted(os.listdir(dirname)):
        if not fname.startswith("upgrade_"):
            continue
        if fname.startswith("upgrade_main"):
            continue
        basename, ext = os.path.splitext(fname)
        mod_name = "handlers.upgrade." + basename
        mod = six._import_module(mod_name)
        logging.info("执行升级: %s", mod_name)
        mod.do_upgrade()

    logging.info("check_upgrade done")

class UpgradeHandler:

    @xauth.login_required("admin")
    def GET(self):
        try:
            check_upgrade()
            return "success"
        except:
            err_msg = xutils.print_exc()
            
            err_log = Storage()
            err_log.time = dateutil.format_datetime()
            err_log.msg = err_msg
            err_log.level = "ERROR"
            err_log.biz_type = "upgrade"

            sys_log_db.insert(err_log)

xutils.register_func("upgrade.is_upgrade_done", is_upgrade_done)
xutils.register_func("upgrade.mark_upgrade_done", mark_upgrade_done)
xutils.register_func("upgrade.main", check_upgrade)

xurls = (
    r"/upgrade/main", UpgradeHandler
)
