# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/31 23:22:49
# @modified 2022/01/01 01:25:13
# @filename upgrade_002.py

import xutils
from xutils import dbutil
from xutils import dateutil

UPGRADE = xutils.DAO("upgrade")
NOTE_DAO = xutils.DAO("note")

def log_info(fmt, *args):
    print(dateutil.format_time(), "[upgrade]", fmt.format(*args))

def do_upgrade():
    """升级入口"""
    if UPGRADE.is_upgrade_done("upgrade_002"):
        log_info("upgrade_002 done")
        return

    db = dbutil.get_table("note_index")
    for note in db.iter(limit = -1):
        if note.is_public:
            log_info("Fix public index:{}", note.id)
            if note.share_time is None:
                note.share_time = note.ctime
            if note.hot_index is None:
                note.hot_index = 1
            NOTE_DAO.update_public_index(note)
            
    UPGRADE.mark_upgrade_done("upgrade_002")
