# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/31 23:06:44
# @modified 2022/01/01 01:26:03
# @filename upgrade_main.py

"""系统升级相关的自动化脚本

使用约定:
1. 升级文件名为`handlers/upgrade/upgrade_03d%.py`
    文件名按数字递增，执行顺序按数字顺序
    可以跳过某些数字
2. 升级文件中的入口为`do_upgrade`
3. 升级文件需要自己处理幂等逻辑，这里提供了幂等表`upgrade_log`
"""

import six
import xmanager
import xutils
from xutils import dbutil
from xutils import dateutil

dbutil.register_table("db_upgrade_log", "数据库升级日志")

def get_upgrade_log_table():
    return dbutil.get_hash_table("db_upgrade_log")

def is_upgrade_done(op_flag):
    db = get_upgrade_log_table()
    return db.get(op_flag) == "1"

def mark_upgrade_done(op_flag):
    db = get_upgrade_log_table()
    db.put(op_flag, "1")

def log_info(fmt, *args):
    print(dateutil.format_time(), "[upgrade]", fmt.format(*args))

def log_error(fmt, *args):
    print(dateutil.format_time(), "[upgrade]", fmt.format(*args))

def log_warn(fmt, *args):
    print(dateutil.format_time(), "[upgrade]", fmt.format(*args))

@xmanager.listen("sys.reload")
def check_upgrade(ctx):
    log_info("check_upgrade...")

    i = 0
    for i in range(10):
        mod_name = "handlers.upgrade.upgrade_%03d" % i
        try:
            mod = six._import_module(mod_name)
        except ImportError:
            log_warn("加载模块失败: {}", mod_name)
            continue

        if hasattr(mod, "do_upgrade"):
            log_info("执行升级:{}", mod_name)
            mod.do_upgrade()

    log_info("check_upgrade done")

xutils.register_func("upgrade.is_upgrade_done", is_upgrade_done)
xutils.register_func("upgrade.mark_upgrade_done", mark_upgrade_done)

