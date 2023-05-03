# -*- coding:utf-8 -*-
# @author mark
# @since 2022/03/12 21:45:37
# @modified 2022/03/12 22:25:56
# @filename upgrade_005.py

import logging

import xutils
from xutils import dbutil
from .base import is_upgrade_done, mark_upgrade_done
from handlers.note.dao import update_children_count

def do_upgrade():
    if is_upgrade_done("upgrade_006"):
        logging.info("upgrade_006 done")
        return
    
    db = dbutil.get_table("notebook")
    
    for item in db.iter(limit=-1):
        update_children_count(item.id)

    mark_upgrade_done("upgrade_006")

