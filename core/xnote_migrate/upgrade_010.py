# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-02-05 16:27:16
@LastEditors  : xupingmao
@LastEditTime : 2023-10-01 00:23:55
@FilePath     : /xnote/core/xnote_migrate/upgrade_010.py
@Description  : 描述
"""
import xauth

from . import base
from handlers.note.dao import get_by_id
from handlers.note.dao_tag import TagBindDao, TagMetaDao


def do_upgrade():
    """修复笔记历史的索引"""
    new_key = "20230205_note_tag"
    old_key = "upgrade_010"
    base.move_upgrade_key(old_key=old_key, new_key=new_key)
    base.execute_upgrade(new_key, fix_user_tag)


def fix_user_tag():
    for user in xauth.iter_user(limit=-1):
        user_name = user.name
        for tag_info in TagBindDao.iter_user_tag(user_name=user_name):
            note_id = tag_info.note_id
            tags = tag_info.tags
            note_info = get_by_id(note_id)
            tag_type = "note"

            if note_info != None:
                TagBindDao.bind_tag(user_name, note_id, tags,
                                    parent_id=note_info.parent_id)
                if note_info.type == "group":
                    tag_type = "group"
                TagMetaDao.update_amount_async(
                    user_name, tags, tag_type=tag_type, parent_id=note_info.parent_id)
