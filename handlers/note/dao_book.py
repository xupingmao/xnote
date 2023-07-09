# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-07-03 09:09:49
@LastEditors  : xupingmao
@LastEditTime : 2023-07-09 11:38:16
@FilePath     : /xnote/handlers/note/dao_book.py
@Description  : 描述
"""
import copy
import xmanager
from xutils import Storage
from xutils import dateutil, dbutil, fsutil
import xutils
import xconfig
from . import dao as note_dao
from .dao import get_by_id, create_note, update_note, list_default_notes, move_note

_db = dbutil.get_table("notebook")
NOTE_DAO = xutils.DAO("note")

def SmartNote(name, url, icon="fa-folder", size=None, size_attr=None):
    note = Storage(name=name, url=url)
    note.priority = 0
    note.icon = icon
    note.size = size
    note.size_attr = size_attr
    return note

def check_and_create_default_book(user_name):
    """检查并且创建默认笔记本"""
    assert user_name != None
    
    def find_default_func(key, value):
        return value.is_default == True
    
    with dbutil.get_write_lock():
        result = _db.list(filter_func = find_default_func, user_name = user_name)
        if len(result) == 0:
            default_book = note_dao.NoteDO()
            default_book.ctime = dateutil.format_datetime()
            default_book.mtime = dateutil.format_datetime()
            default_book.name = "默认笔记本"
            default_book.content = ""
            default_book.creator = user_name
            default_book.is_default = True
            default_book.is_public = 0
            default_book.type = "group"
            default_book.priority = 1
            default_book.children_count = 0
            default_book.size = 0
            default_book.is_deleted = 0

            default_book_id = create_note(default_book, check_name=False)

        else:
            note_info = result[0]
            default_book_id = note_info.id
            
            update_kw = note_dao.NoteDO()
            update_kw.type = "group"
            update_kw.priority = 1
            update_kw.is_default = True
            update_kw.is_public = 0
            update_kw.children_count = 0
            update_kw.is_deleted = 0
            update_kw.size = 0

            update_note(default_book_id, **update_kw)
        
        for note in list_default_notes(user_name):
            move_note(note, default_book_id)
    
        return default_book_id


def fix_book_delete(id, user_name):
    note = get_by_id(id)
    book = _db.get_by_id(id, user_name=user_name)
    if note == None and book != None:
        _db.delete(book)


def get_default_book_id(user_name):
    assert user_name != None, "user_name不能为空"
    first = _db.get_first(user_name = user_name)
    if first == None:
        return check_and_create_default_book(user_name)
    return first.id

class SmartGroupService:

    SMART_GROUP_COUNT = 0
    _smart_groups = []

    @classmethod
    def init(cls):
        cls._smart_groups = cls.load_smart_groups_template()
        cls.list_smart_group("admin")

    @staticmethod
    def load_smart_groups_template():
        fpath = xconfig.resolve_config_path("./config/note/smart_group.ini")
        config = fsutil.load_ini_config(fpath)
        result = []
        for key in config.sections:
            item = config.items[key]
            if item.visible == "false":
                continue
            note = SmartNote(item.name, item.url, size_attr=item.size_attr)
            result.append(note)
        return result


    @classmethod
    def list_smart_group(cls, user_name):
        note_stat = note_dao.get_note_stat(user_name)
        smart_group_list = copy.deepcopy(cls._smart_groups)

        for item in smart_group_list:
            if item.size_attr != None:
                size = getattr(note_stat, item.size_attr)
                item.size = size
                item.badge_info = size

        cls.SMART_GROUP_COUNT = len(smart_group_list)
        return smart_group_list


    @classmethod
    def count_smart_group(cls, user_name=None):
        return cls.SMART_GROUP_COUNT

@xmanager.listen("user.create")
def on_create_user(event):
    pass

@xmanager.listen("sys.reload")
def on_reload(ctx):
    SmartGroupService.init()


SmartGroupService.init()
xutils.register_func("note.count_smart_group", SmartGroupService.count_smart_group)
xutils.register_func("note.list_smart_group", SmartGroupService.list_smart_group)
xutils.register_func("note.get_default_book_id", get_default_book_id)
