# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-07-14 22:51:33
@LastEditors  : xupingmao
@LastEditTime : 2023-01-28 23:08:03
@FilePath     : /xnote/handlers/note/dao_read.py
@Description  : 读操作
"""

from handlers.note.dao import list_by_parent
import xutils
from xutils import Storage


def get_note_depth(note, max_recursive=10):
    # type: (Storage, int) -> int
    """计算笔记的深度"""
    assert note != None
    assert note.type == "group"

    if max_recursive <= 0:
        return 0

    max_depth = 1

    for item in list_by_parent(note.creator, parent_id = note.id):
        if item.type == "group":
            depth = get_note_depth(item, max_recursive-1)
            max_depth = max(max_depth, depth+1)
            
    return max_depth

xutils.register_func("note.get_depth", get_note_depth)
