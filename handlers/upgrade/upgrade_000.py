# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/31 23:27:42
# @modified 2022/01/08 11:09:03
# @filename upgrade_000.py

"""升级的demo"""

import xutils
from xutils import dbutil
from xutils import dateutil
from handlers.upgrade.upgrade_main import log_info
from handlers.upgrade.upgrade_main import is_upgrade_done
from handlers.upgrade.upgrade_main import mark_upgrade_done

def do_upgrade():
    log_info("this is upgrade demo")