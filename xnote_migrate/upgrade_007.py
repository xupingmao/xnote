# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-06-26 12:01:10
@LastEditors  : xupingmao
@LastEditTime : 2023-10-01 00:25:22
@FilePath     : /xnote/core/xnote_migrate/upgrade_007.py
@Description  : 描述
"""


from xutils import dbutil
from . import base
from handlers.note import dao_comment

def do_upgrade():
    # 20220626
    old_key = "upgrade_007"
    new_key = "20220626_fix_comment"
    base.move_upgrade_key(old_key, new_key)
    base.execute_upgrade(new_key, upgrade_comment)

def upgrade_comment():
    dbutil.register_table("note_comment", "笔记评论")
    db = dbutil.get_table("note_comment")
    
    dao_comment.drop_comment_table()
    for item in db.iter(limit=-1):
        dao_comment.fix_comment(item)

