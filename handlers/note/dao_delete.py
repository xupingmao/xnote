# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-08-20 16:53:16
@LastEditors  : xupingmao
@LastEditTime : 2023-07-02 14:27:39
@FilePath     : /xnote/handlers/note/dao_delete.py
@Description  : 删除的处理
"""

import xutils
from xutils import dbutil
from .dao_api import NoteDao
from .dao import (
    delete_history,
    add_history,
    get_by_id,
    update_children_count,
    put_note_to_db,
    delete_note_skey,
    refresh_note_stat,
    get_note_tiny_table,
    _full_db,
    _book_db
)

from .dao_tag import delete_tags

def delete_note_physically(creator, note_id):
    assert creator != None, "creator can not be null"
    assert note_id != None, "note_id can not be null"

    index_key = "note_index:%s" % note_id

    _full_db.delete_by_id(note_id)
    dbutil.delete(index_key)

    note_tiny_db = get_note_tiny_table(creator)
    note_tiny_db.delete_by_id(note_id)

    delete_history(note_id)


def delete_note(id):
    note = get_by_id(id)
    if note is None:
        return

    if note.is_deleted != 0:
        # 已经被删除了，执行物理删除
        delete_note_physically(note.creator, note.id)
        return

    # 标记删除
    note.mtime = xutils.format_datetime()
    note.dtime = xutils.format_datetime()
    note.is_deleted = 1
    put_note_to_db(id, note)

    # 更新数量
    update_children_count(note.parent_id)
    delete_tags(note.creator, id)

    # 删除笔记本
    _book_db.delete_by_id(id, user_name=note.creator)

    # 删除skey索引
    delete_note_skey(note)

    # 删除访问日志
    NoteDao.delete_visit_log(note.creator, note.id)

def recover_note(id):
    """恢复删除的笔记"""
    note = get_by_id(id)
    if note is None:
        return
    
    if note.is_deleted == 0:
        return
    
    note.mtime = xutils.format_datetime()
    note.is_deleted = 0
    note.version = note.version + 1
    
    # 记录变更日志
    add_history(id, note.version, note)
    # 更新数据
    put_note_to_db(id, note)
    
    # 更新数量
    update_children_count(note.parent_id)

xutils.register_func("note.delete", delete_note)
xutils.register_func("note.delete_physically", delete_note_physically)


NoteDao.delete_note = delete_note
