# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2022/01/08 11:04:03
# @modified 2022/01/08 12:15:00
# @filename upgrade_004.py

"""note_public索引重建"""

from xutils import dbutil
from . import base


def do_upgrade():
    mark_key = "upgrade_004.2"
    new_key = "20220108_fix_share_time"
    base.move_upgrade_key(old_key=mark_key, new_key=new_key)
    base.execute_upgrade(new_key, fix_share_time)

def fix_share_time():
    db = dbutil.get_table("note_public")
    for value in db.iter(limit = -1):
        if value.share_time is None:
            value.share_time = value.ctime
            db.update(value)
        db.rebuild_single_index(value)

