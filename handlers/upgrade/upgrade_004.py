# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2022/01/08 11:04:03
# @modified 2022/01/08 12:15:00
# @filename upgrade_004.py

"""note_public索引重建"""

import xutils
from xutils import dbutil
from xutils import dateutil
from handlers.upgrade.upgrade_main import log_info
from handlers.upgrade.upgrade_main import is_upgrade_done
from handlers.upgrade.upgrade_main import mark_upgrade_done

def do_upgrade():
    if is_upgrade_done("upgrade_004.2"):
        log_info("upgrade_004 done")
        return

    db = dbutil.get_table("note_public")
    for value in db.iter(limit = -1):
        if value.share_time is None:
            value.share_time = value.ctime
            db.update(value)
        db.rebuild_single_index(value)

    mark_upgrade_done("upgrade_004.2")

