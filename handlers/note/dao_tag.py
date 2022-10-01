# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-08-20 15:46:37
@LastEditors  : xupingmao
@LastEditTime : 2022-10-01 14:21:14
@FilePath     : /xnote/handlers/note/dao_tag.py
@Description  : 标签
"""

import json
import xutils
from xutils import dbutil
from xutils import attrget, Storage
from .dao import get_by_id, update_index, sort_notes

tags_db = dbutil.get_table("note_tags")
tag_meta_db = dbutil.get_table("note_tag_meta")

def get_tags(creator, note_id):
    note_tags = tags_db.get_by_id(note_id, user_name = creator)
    if note_tags:
        return attrget(note_tags, "tags")
    return None


def get_tag_meta_by_name(user_name, tag_name, tag_type = "group", group_id = None):
    result = list_tag_meta(user_name, limit = 1, tag_type = tag_type, group_id=group_id, tag_name=tag_name)
    if len(result) > 0:
        return result[0]
    return None

def list_tag_meta(user_name, *, limit = 1000, tag_type="group", tag_name=None, group_id = None):
    if tag_type == "note":
        assert group_id != None, "group_id不能为空"
        
    def list_tag_meta_func(key, value):
        if not value.tag_type == tag_type:
            return False
        if tag_name != None and value.tag_name != tag_name:
            return False
        if group_id != None and value.group_id != group_id:
            return False
        return True
    return tag_meta_db.list(limit = limit, filter_func = list_tag_meta_func, user_name = user_name)

def update_tags(creator, note_id, tags):
    tags_db.update_by_id(note_id, Storage(note_id=note_id, user=creator, tags=tags))

    note = get_by_id(note_id)
    if note != None:
        note.tags = tags
        update_index(note)


def delete_tags(creator, note_id):
    tags_db.delete_by_id(note_id, user_name=creator)


def list_by_tag(user, tagname):
    if user is None:
        user = "public"

    def list_func(key, value):
        if value.tags is None:
            return False
        return tagname in value.tags

    tags = tags_db.list(filter_func=list_func, user_name = user)
    files = []
    for tag in tags:
        note = get_by_id(tag.note_id)
        if note != None:
            files.append(note)
    sort_notes(files)
    return files

def batch_get_tags_by_notes(notes):
    result = dict()
    if len(notes) == 0:
        return result

    id_list = []
    for note in notes:
        id_list.append(note.id)
    
    creator = notes[0].creator
    tags_dict = tags_db.batch_get_by_id(id_list, user_name = creator)
    
    for note in notes:
        tag_info = tags_dict.get(note.id)
        tags = []
        if tag_info != None and tag_info.tags != None:
            tags = tag_info.tags

        result[note.id] = tags
        note.tags_json = json.dumps(tags)
    return result

def list_tag(user):
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

    tags_db.count(filter_func=list_func, user_name = user)

    tag_list = [Storage(name=k, amount=tags[k]) for k in tags]
    tag_list.sort(key=lambda x: -x.amount)
    return tag_list

xutils.register_func("note.list_tag", list_tag)
xutils.register_func("note.list_by_tag", list_by_tag)
xutils.register_func("note.get_tags", get_tags)
xutils.register_func("note.update_tags", update_tags)
xutils.register_func("note_tag_meta.get_by_name", get_tag_meta_by_name)
xutils.register_func("note_tag_meta.list", list_tag_meta)