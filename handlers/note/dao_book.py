# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-07-03 09:09:49
@LastEditors  : xupingmao
@LastEditTime : 2022-07-09 09:18:04
@FilePath     : /xnote/handlers/note/dao_book.py
@Description  : 描述
"""
import threading
from xutils import Storage
from xutils import dateutil, dbutil
from .dao import get_by_id, create_note, update_note, list_default_notes, move_note

_db = dbutil.get_table("notebook")
_lock = threading.RLock()

def check_and_create_default_book(user_name):
    """检查并且创建默认笔记本"""
    assert user_name != None
    
    def find_default_func(key, value):
        return value.is_default == True
    
    with _lock:
        result = _db.list(filter_func = find_default_func, user_name = user_name)
        if len(result) == 0:
            default_book = Storage()
            default_book.ctime = dateutil.format_datetime()
            default_book.mtime = dateutil.format_datetime()
            default_book.name = "默认笔记本"
            default_book.content = ""
            default_book.creator = user_name
            default_book.is_default = True
            default_book.is_public = False
            default_book.type = "group"
            default_book.priority = 1
            default_book.children_count = 0
            default_book.size = 0
            default_book.is_deleted = 0

            default_book_id = create_note(default_book, check_name=False)

        else:
            note_info = result[0]
            default_book_id = note_info.id
            
            update_kw = Storage()
            update_kw.type = "group"
            update_kw.priority = 1
            update_kw.is_default = True
            update_kw.is_public = False
            update_kw.children_count = 0
            update_kw.is_deleted = 0
            update_kw.size = 0

            update_note(default_book_id, **update_kw)
        
        for note in list_default_notes(user_name):
            move_note(note, default_book_id)


def fix_book_delete(id, user_name):
    note = get_by_id(id)
    book = _db.get_by_id(id, user_name=user_name)
    if note == None and book != None:
        _db.delete(book)
