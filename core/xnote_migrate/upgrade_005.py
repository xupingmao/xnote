# -*- coding:utf-8 -*-
# @author mark
# @since 2022/03/12 21:45:37
# @modified 2022/03/12 22:25:56
# @filename upgrade_005.py

import logging

import xutils
from xutils import dbutil
from .base import is_upgrade_done, mark_upgrade_done

from handlers.note.dao_share import share_note_to

NOTE_DAO = xutils.DAO("note")

def do_upgrade():
    if is_upgrade_done("upgrade_005"):
        logging.info("upgrade_005 done")
        return

    dbutil.register_table("note_share_from", "分享发送者关系表 <note_share_from:from_user:note_id>")
    db = dbutil.get_table("note_share_from")
    for value in db.iter(limit = -1):
        note_id = value.note_id
        to_user_list = value.share_to_list

        note = NOTE_DAO.get_by_id(note_id)
        if note != None:
            for to_user in to_user_list:
                share_note_to(note, note.creator, to_user)

    mark_upgrade_done("upgrade_005")

