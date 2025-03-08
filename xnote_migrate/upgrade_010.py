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

from xnote.core import xauth
from . import base
from handlers.note.dao import get_by_id
from xutils import dbutil
from xutils import BaseDataRecord
from xutils.numutil import parse_int
from xnote.service.tag_service import NoteTagBindService

# TODO 创建测试用例覆盖
def do_upgrade():
    """修复笔记历史的索引"""
    new_key = "20230205_note_tag"
    old_key = "upgrade_010"
    base.move_upgrade_key(old_key=old_key, new_key=new_key)
    base.execute_upgrade(new_key, fix_user_tag)

class TagBind(BaseDataRecord):
    """标签绑定信息"""
    def __init__(self, **kw):
        self.note_id = ""
        self.user = ""
        self.tags = []
        self.parent_id = ""
        self.update(kw)


def fix_user_tag():
    tag_bind_kv = dbutil.get_table("note_tags")
    for item in tag_bind_kv.iter(limit=-1):
        tag_info = TagBind(**item)
        note_id = parse_int(tag_info.note_id)
        tags = tag_info.tags
        note_info = get_by_id(note_id)
        if note_info != None and note_id > 0:
            user_id = note_info.creator_id
            NoteTagBindService.bind_tags(user_id=user_id, target_id=note_id, tags=tags)
