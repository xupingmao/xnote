# -*- coding:utf-8 -*-
# @author mark
# @since 2022/03/12 21:45:37
# @modified 2022/03/12 22:25:56
# @filename upgrade_005.py

import logging
import xutils
import handlers.note.dao as note_dao
from xutils import dbutil
from . import base

def do_upgrade():
    old_key = "upgrade_006"
    new_key = "20220312_fix_children_count"
    base.move_upgrade_key(old_key, new_key)
    base.execute_upgrade(new_key, fix_children_count)

def fix_children_count():
    db = dbutil.get_table("notebook")
    
    for item in db.iter(limit=-1):
        note_dao.update_children_count(item.id)


