# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-08-20 15:46:37
@LastEditors  : xupingmao
@LastEditTime : 2023-10-22 23:47:21
@FilePath     : /xnote/handlers/note/dao_tag.py
@Description  : 标签
"""

import json
import xutils
import xtables
import xauth
import logging
import handlers.note.dao as note_dao
from xutils import functions, lists
from xutils import dbutil
from xutils import attrget, Storage
from handlers.note.dao_api import NoteDao
from xnote.service import TagBindService, TagTypeEnum

tag_bind_db = dbutil.get_table("note_tags")
tag_meta_db = dbutil.get_table("note_tag_meta")

class TagBind(Storage):
    """标签绑定信息"""
    def __init__(self, **kw):
        self.note_id = ""
        self.user_name = ""
        self.tags = []
        self.parent_id = ""
        self.update(kw)

    @classmethod
    def from_dict(cls, dict_value):
        if dict_value == None:
            return None
        bind = TagBind()
        bind.update(dict_value)
        return bind

class TagMeta(Storage):
    """标签元信息"""
    def __init__(self, **kw):
        self.user = ""
        self.tag_name = ""
        self.tag_code = ""
        self.tag_type = "" # group - 笔记本标签 note-笔记标签 global-全局标签(不分区笔记本还是笔记)
        self.amount = 0
        self.book_id = ""
        self.group_id = ""
        self.update(kw)

class NoteTagRelation(Storage):
    """笔记和标签的关系表"""
    def __init__(self):
        self.ctime = xutils.format_datetime()
        self.user_id = 0
        self.note_id = ""
        self.tag_code = ""

class TagInfo(Storage):
    def __init__(self, name = "", code = "", amount = 0) -> None:
        self.name = name
        self.code = code
        self.amount = amount
        self.url = ""

def get_tags(creator, note_id):
    note_tags = tag_bind_db.get_by_id(note_id, user_name=creator)
    if note_tags:
        return attrget(note_tags, "tags")
    return None


class TagBindDao:
    """标签绑定信息"""
    tag_bind_service = TagBindService(TagTypeEnum.note_tag)

    @classmethod
    def bind_tag(cls, user_name="", note_id=0, tags=[], parent_id=None):
        tag_bind_db.update_by_id(note_id, Storage(
            note_id=note_id, user=user_name, tags=tags, parent_id=parent_id))
        
        user_info = xauth.get_user_by_name(user_name)
        assert user_info != None
        cls.update_tag_bind(user_info.id, note_id, tags)

    @staticmethod
    def get_by_note_id(user_name, note_id):
        record = tag_bind_db.get_by_id(note_id, user_name=user_name)
        return TagBind.from_dict(record)

    @staticmethod
    def count_user_tag(user_name = "", tag_name = "", parent_id=None):
        assert user_name != ""
        assert tag_name != ""
        
        def filter_func(key, value):
            if tag_name not in value.tags:
                return False
            if parent_id != None and value.parent_id != parent_id:
                return False
            if value.user != user_name:
                return False
            return True
        return tag_bind_db.count_by_func(user_name=user_name, filter_func=filter_func)

    @staticmethod
    def iter_user_tag(user_name, limit=-1):
        for value in tag_bind_db.iter(user_name=user_name, limit=limit):
            yield TagBind(**value)
        
    @classmethod    
    def get_uniq_tags(cls, new_tags=[]):
        return lists.get_uniq_list(new_tags)
    
    @classmethod
    def update_tag_bind(cls, user_id=0, note_id="", new_tags=[]):
        cls.tag_bind_service.bind_tags(user_id=user_id, target_id=int(note_id), tags=new_tags)

    @classmethod
    def is_not_sys_tag(cls, tag_info: TagInfo):
        return tag_info.name not in static_code_map

    @classmethod
    def list_tag(cls, user, exclude_sys_tag=False):
        if user is None:
            user = "public"

        tags = dict()

        def list_func(key, value):
            if value.tags is None:
                return False
            for tag in value.tags:
                count = tags.get(tag, 0)
                count += 1
                tags[tag] = count

        tag_bind_db.count(filter_func=list_func, user_name=user)

        tag_list = [TagInfo(name=k, amount=tags[k]) for k in tags]
        
        if exclude_sys_tag:
            tag_list = list(filter(cls.is_not_sys_tag, tag_list))

        tag_list.sort(key=lambda x: -x.amount)
        return tag_list


class TagMetaDao:
    """标签元信息"""

    @staticmethod
    def check_tag_type(tag_type):
        # global包含全部的标签
        # note是笔记上的标签
        # TODO group改成suggest可能更合适一些
        assert tag_type in ("group", "global", "note")

    @staticmethod
    def update(tag_info):
        tag_meta_db.update(tag_info)

    @staticmethod
    def delete(tag_info):
        tag_meta_db.delete(tag_info)

    @staticmethod
    def create(tag_info: TagMeta):
        assert tag_info.user != ""
        assert tag_info.tag_name != ""
        assert tag_info.tag_type != ""
        assert tag_info.amount != None
        tag_meta_db.insert(tag_info)

    @classmethod
    def get_by_name(cls, user_name, tag_name, tag_type="", group_id=None):
        cls.check_tag_type(tag_type)
        result = list_tag_meta(
            user_name, limit=1, tag_type=tag_type, group_id=group_id, tag_name=tag_name)
        if len(result) > 0:
            return TagMeta(**result[0])
        return None

    @classmethod
    @xutils.async_func_deco()
    def update_amount_async(cls, user_name: str, tag_names: list, tag_type: str, parent_id=None):
        for tag_name in tag_names:
            tag_info = get_tag_meta_by_name(
                user_name, tag_name, tag_type=tag_type, group_id=parent_id)
            if tag_info != None:
                tag_info.amount = TagBindDao.count_user_tag(
                    user_name, tag_name, parent_id=parent_id)
                cls.update(tag_info)

    @classmethod
    @xutils.async_func_deco()
    def update_global_amount_async(cls, user_name: str, tag_names: list):
        for tag_name in tag_names:
            tag_info = cls.get_by_name(
                user_name = user_name, tag_name = tag_name, tag_type="global")
            amount = TagBindDao.count_user_tag(user_name, tag_name)
            if amount == 0:
                if tag_info == None:
                    return
                else:
                    cls.delete(tag_info)
                return

            if tag_info != None:
                tag_info.amount = amount
                cls.update(tag_info)
            else:
                tag_info = TagMeta()
                tag_info.user = user_name
                tag_info.tag_name = tag_name
                tag_info.tag_type = "global"
                tag_info.amount = amount
                cls.create(tag_info)

    @classmethod
    def is_empty(cls, value):
        return value == None or value == ""
    
    @classmethod
    def is_not_sys_tag(cls, tag_info: TagMeta):
        return tag_info.tag_code not in static_code_map

    @classmethod
    def list_meta(cls, user_name, *, limit=1000, tag_type="group", 
                  tag_name=None, group_id=None, 
                  include_sys_tag=True):
        if tag_type == "note":
            assert group_id != None, "group_id不能为空"
        
        where = {
            "tag_type": tag_type,
        }

        if tag_name != None:
            where["tag_name"] = tag_name
        if group_id != None:
            where["group_id"] = str(group_id)
        
        result = tag_meta_db.list(
            limit=limit, where = where, user_name=user_name)
        
        if not include_sys_tag:
            result = list(filter(cls.is_not_sys_tag, result))

        for item in result:
            if cls.is_empty(item.tag_code):
                item.tag_code = item.tag_name

        result.sort(key=lambda x: x.amount or 0, reverse=True)
        return result


def get_tag_meta_by_name(user_name, tag_name, tag_type="group", group_id=None):
    result = list_tag_meta(
        user_name, limit=1, tag_type=tag_type, group_id=group_id, tag_name=tag_name)
    if len(result) > 0:
        return TagMeta(**result[0])
    return None

list_tag_meta = TagMetaDao.list_meta


def count_tag(user_name):
    return tag_meta_db.count_by_user(user_name=user_name)


def bind_tags(creator, note_id, tags, tag_type="group"):
    assert isinstance(tags, list)
    note = note_dao.get_by_id(note_id)
    assert note != None, "笔记不存在"
    
    tags = TagBindDao.get_uniq_tags(tags)
    
    old_tag_bind = TagBindDao.get_by_note_id(creator, note_id)
    old_tags = []
    if old_tag_bind != None:
        old_tags = old_tag_bind.tags
    
    if old_tags == tags:
        logging.info("笔记标签没有变化,tags=%s", tags)
        return

    TagBindDao.bind_tag(creator, note_id, tags, parent_id=note.parent_id)

    note.tags = tags
    note_dao.update_index(note)

    # 老的tag也需要更新
    if old_tag_bind != None:
        for tag in functions.safe_list(old_tag_bind.tags):
            if tag not in tags:
                tags.append(tag)
    
    TagMetaDao.update_amount_async(
        creator, tags, tag_type, parent_id=note.parent_id)
    TagMetaDao.update_global_amount_async(creator, tags)


update_tags = bind_tags


def delete_tags(creator, note_id):
    tag_bind_db.delete_by_id(note_id, user_name=creator)

def list_by_tag(user="", tagname = "", limit = 1000):
    # TODO 优化查询性能
    if user == "":
        user = "public"
        
    def list_func(key, value):
        if value.tags is None:
            return False
        return tagname in value.tags

    tags = tag_bind_db.list(filter_func=list_func, user_name=user, limit = limit)
    note_ids = []
    for tag in tags:
        note_ids.append(tag.note_id)
    notes = note_dao.batch_query_list(note_ids)
    note_dao.sort_notes(notes, orderby="mtime_desc")
    note_dao.sort_by_ctime_priority(notes)
    return notes


def batch_get_tags_by_notes(notes):
    result = dict()
    if len(notes) == 0:
        return result

    id_list = []
    for note in notes:
        id_list.append(str(note.id))

    creator = notes[0].creator
    tags_dict = tag_bind_db.batch_get_by_id(id_list, user_name=creator)

    for note in notes:
        tag_info = tags_dict.get(note.id)
        tags = []
        if tag_info != None and tag_info.tags != None:
            tags = tag_info.tags

        result[note.id] = tags
        note.tags_json = json.dumps(tags)
    return result

def get_system_tag_list(tag_list=None):
    result = [
        TagInfo(code="$todo$", name="待办", amount=0),
    ]
    if tag_list != None:
        tag_count_map = dict()
        for item in tag_list:
            tag_count_map[item.name] = item.amount
        for item in result:
            item.amount = tag_count_map.get(item.code, 0)

    return result


def get_system_tag_code_map():
    result = {}
    for item in get_system_tag_list():
        result[item.code] = item.name
    return result


static_code_map = get_system_tag_code_map()

def get_user_defined_tags(tag_list):
    result = []
    for item in tag_list:
        if item.name not in static_code_map:
            result.append(item)
    return result

def get_name_by_code(code):
    return static_code_map.get(code, code)

def handle_tag_for_note(note_info):
    note = note_info
    if note.tags == None:
        note.tags = []
    note.tags_json = xutils.tojson(note.tags)
    tag_info_list = []
    for tag_code in note.tags:
        tag_name = get_name_by_code(tag_code)
        tag_info = TagInfo(code = tag_code, name = tag_name)
        tag_info.url = "/note/tagname/%s" % xutils.quote(tag_code)

        tag_info_list.append(tag_info)
    note.tag_info_list = tag_info_list


def append_tag(note_id=0, tag_code=""):
    """向笔记追加标签"""
    note_info = note_dao.get_by_id(note_id)
    if note_info == None:
        raise Exception("笔记不存在")
    tags = note_info.tags
    assert isinstance(tags, list)
    tags.append(tag_code)
    bind_tags(note_info.creator, note_id, tags)

list_tag = TagBindDao.list_tag


xutils.register_func("note.list_tag", list_tag)
xutils.register_func("note.list_by_tag", list_by_tag)
xutils.register_func("note.get_tags", get_tags)
xutils.register_func("note.update_tags", bind_tags)
xutils.register_func("note_tag_meta.get_by_name", get_tag_meta_by_name)
xutils.register_func("note_tag_meta.list", list_tag_meta)
xutils.register_func("note_tag.get_name_by_code", get_name_by_code)

NoteDao.count_tag = count_tag
