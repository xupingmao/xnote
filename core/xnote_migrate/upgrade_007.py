# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-06-26 12:01:10
@LastEditors  : xupingmao
@LastEditTime : 2022-06-26 15:48:49
@FilePath     : /xnote/handlers/upgrade/upgrade_007.py
@Description  : 描述
"""


import logging
from xutils import dbutil
from .base import is_upgrade_done, mark_upgrade_done
from handlers.note.dao_comment import fix_comment, drop_comment_table

def do_upgrade():
    upgrade_key = "upgrade_007"

    if is_upgrade_done(upgrade_key):
        logging.info("%s done" % upgrade_key)
        return
    
    dbutil.register_table("note_comment", "笔记评论")
    db = dbutil.get_table("note_comment")

    drop_comment_table()
    for item in db.iter(limit=-1):
        fix_comment(item)
        
    mark_upgrade_done(upgrade_key)

