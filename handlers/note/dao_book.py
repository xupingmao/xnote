# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-07-03 09:09:49
@LastEditors  : xupingmao
@LastEditTime : 2023-09-17 17:50:46
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
from .dao import get_by_id, check_and_create_default_book

NOTE_DAO = xutils.DAO("note")

def SmartNote(name, url, icon="fa-folder", size=None, size_attr=None):
    note = Storage(name=name, url=url)
    note.priority = 0
    note.icon = icon
    note.size = size
    note.size_attr = size_attr
    return note

def fix_book_delete(id, user_name):
    pass

def get_default_book_id(user_name):
    return check_and_create_default_book(user_name)

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
