# -*- coding:utf-8 -*-
# @author mark
# @since 2022/04/04 14:49:25
# @modified 2022/04/04 15:49:07
# @filename dao_draft.py

"""笔记草稿的处理，正常编辑的步骤

def edit():
    if lock_for_edit():
        do_edit()
    else:
        if want_steal_lock():
            steal_edit_lock()
            do_edit()

def do_edit():
    content = get_draft()
    while is_editing():
        refresh_edit_lock()
        save_draft()
"""

import time
import xutils
from xutils import dbutil
from xutils import Storage

NOTE_DAO = xutils.DAO("note")
dbutil.register_table("note_draft", "笔记草稿", "note")
dbutil.register_table("note_lock", "笔记编辑锁", "note")


def get_note_draft_db():
    return dbutil.get_hash_table("note_draft")

def get_note_lock_db():
    return dbutil.get_hash_table("note_lock")

def is_valid_token(lock_info):
    return lock_info.expire_time > time.time()

def lock_for_edit(note_id, token):
    assert isinstance(note_id, str)
    assert isinstance(token, str)

    db = get_note_lock_db()
    lock_info = db.get(note_id)
    if lock_info == None or not is_valid_token(lock_info):
        return True
    return token == lock_info.token

def save_draft(note_id, content):
    """
    @param {string} note_id 笔记ID
    @param {string} content 笔记内容
    """
    assert isinstance(note_id, str)
    assert isinstance(content, str)

    db = get_note_draft_db()
    db.put(note_id, content)

def get_draft(note_id):
    assert isinstance(note_id, str)

    db = get_note_draft_db()
    return db.get(note_id)

def steal_edit_lock(note_id, token, expire_time):
    assert isinstance(note_id, str)
    assert isinstance(token, str)
    assert isinstance(expire_time, float)

    lock_info = Storage(token = token, expire_time = expire_time)
    db = get_note_lock_db()
    db.put(note_id, lock_info)

def refresh_edit_lock(note_id, token, expire_time):
    # 应用层需要加锁
    if lock_for_edit(note_id, token):
        steal_edit_lock(note_id, token, expire_time)
        return True
    else:
        return False

xutils.register_func("note.save_draft", save_draft)
xutils.register_func("note.get_draft", get_draft)
xutils.register_func("note.lock_for_edit", lock_for_edit)
xutils.register_func("note.steal_edit_lock", steal_edit_lock)
xutils.register_func("note.refresh_edit_lock", refresh_edit_lock)
