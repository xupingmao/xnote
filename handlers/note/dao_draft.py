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

class NoteLockDO(Storage):
    def __init__(self):
        self.token = ""
        self.note_id = ""
        self.expire_time = 0.0

    @classmethod
    def from_dict(cls, dict_value):
        if dict_value == None:
            return None
        result = NoteLockDO()
        result.update(dict_value)
        return result

class NoteLockDao:
    db = dbutil.get_hash_table("note_lock")

    @classmethod
    def get_by_note_id(cls, note_id=""):
        lock_dict = cls.db.get(note_id)
        return NoteLockDO.from_dict(lock_dict)
    
    @staticmethod
    def is_valid_token(lock_info):
        return lock_info.expire_time > time.time()

    @classmethod
    def lock_for_edit(cls, note_id, token):
        assert isinstance(token, str)
        note_id = str(note_id)
        lock_info = cls.get_by_note_id(note_id)
        if lock_info == None or not cls.is_valid_token(lock_info):
            return True
        return token == lock_info.token

    @classmethod
    def steal_edit_lock(cls, note_id, token, expire_time):
        assert isinstance(token, str)
        assert isinstance(expire_time, float)

        note_id = str(note_id)
        lock_info = Storage(token = token, expire_time = expire_time)
        cls.db.put(note_id, lock_info)
    
    @classmethod
    def refresh_edit_lock(cls, note_id, token, expire_time):
        # 应用层需要加锁
        if cls.lock_for_edit(note_id, token):
            cls.steal_edit_lock(note_id, token, expire_time)
            return True
        else:
            return False
        

class DraftDao:
    db = dbutil.get_hash_table("note_draft")

    @classmethod
    def exists(cls, note_id=0):
        return cls.db.get(str(note_id)) not in (None, "")

def get_note_draft_db():
    return DraftDao.db

def get_note_lock_db():
    return NoteLockDao.db


def lock_for_edit(note_id, token):
    return NoteLockDao.lock_for_edit(note_id, token)

def save_draft(note_id, content=""):
    """
    @param {string} note_id 笔记ID
    @param {string} content 笔记内容
    """

    note_id = str(note_id)
    db = get_note_draft_db()
    if content=="":
        db.delete(note_id)
    else:
        db.put(note_id, content)

def get_draft(note_id):
    note_id = str(note_id)

    db = get_note_draft_db()
    return db.get(note_id)

def steal_edit_lock(note_id, token, expire_time):
    return NoteLockDao.steal_edit_lock(note_id, token, expire_time)

def refresh_edit_lock(note_id, token, expire_time):
    return NoteLockDao.refresh_edit_lock(note_id, token, expire_time)

xutils.register_func("note.save_draft", save_draft)
xutils.register_func("note.get_draft", get_draft)
xutils.register_func("note.lock_for_edit", lock_for_edit)
xutils.register_func("note.steal_edit_lock", steal_edit_lock)
xutils.register_func("note.refresh_edit_lock", refresh_edit_lock)
