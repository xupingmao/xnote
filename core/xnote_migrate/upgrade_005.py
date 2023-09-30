# -*- coding:utf-8 -*-
# @author mark
# @since 2022/03/12 21:45:37
# @modified 2022/03/12 22:25:56
# @filename upgrade_005.py

from xutils import dbutil
from . import base
from handlers.note import dao as note_dao
from handlers.note.dao_share import share_note_to


def do_upgrade():
    old_key = "upgrade_005"
    base.execute_upgrade(old_key, fix_note_share)


def fix_note_share():
    dbutil.register_table("note_share_from", "分享发送者关系表 <note_share_from:from_user:note_id>")
    db = dbutil.get_table("note_share_from")
    for value in db.iter(limit = -1):
        note_id = value.note_id
        to_user_list = value.share_to_list

        note = note_dao.get_by_id(note_id)
        if note != None:
            for to_user in to_user_list:
                share_note_to(note.id, note.creator, to_user)

