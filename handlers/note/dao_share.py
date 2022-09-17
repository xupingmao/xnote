# -*- coding:utf-8 -*-
# @author mark
# @since 2022/03/12 18:57:19
# @modified 2022/03/12 23:21:48
# @filename dao_share.py

import json

import xutils
import xauth
import xconfig
from xutils import Storage
from xutils import dbutil
from xutils import logutil

from .dao import sort_notes, batch_query_list

def register_note_table(name, description, check_user = False):
    dbutil.register_table(name, description, "note", check_user = check_user)

def get_share_db():
    return dbutil.get_table("note_share")

def check_not_empty(value, method_name):
    if value == None or value == "":
        raise Exception("[%s] can not be empty" % method_name)

def args_convert_func(note, from_user, to_user):
    obj = Storage(note_id = note.id, from_user = from_user, to_user = to_user)
    return json.dumps(obj)


def get_share_by_note_and_to_user(note_id, to_user):
    def find_func(key, record):
        return record.to_user == to_user

    db = get_share_db()
    records = db.list_by_index("note_id", index_value = note_id, filter_func = find_func)
    if len(records) > 0:
        return records[0]
    return None


@logutil.log_deco("share_note_to", log_args = True, args_convert_func = args_convert_func)
def share_note_to(note, from_user, to_user):
    # TODO 记录到笔记表中
    if not xauth.is_user_exist(to_user):
        raise Exception("[share_note_to] user not exist: %s" % to_user)

    db = get_share_db()

    record = get_share_by_note_and_to_user(note.id, to_user)
    if record != None:
        # 已经分享了
        return

    record = Storage(from_user = from_user, to_user = to_user, note_id = note.id)
    db.insert(record)

@logutil.log_deco("delete_share", log_args = True)
def delete_share(note_id, to_user):
    record = get_share_by_note_and_to_user(note_id, to_user)
    if record != None:
        db = get_share_db()
        db.delete(record)

def list_share_to(to_user, offset = 0, limit = None, orderby = None):
    if limit is None:
        limit = xconfig.PAGE_SIZE

    db = get_share_db()
    records = db.list_by_index("to_user", index_value = to_user, offset = offset, limit = limit)
    id_list = list(map(lambda x:x.note_id, records))
    notes = batch_query_list(id_list)
    sort_notes(notes, orderby = orderby)
    return notes

def list_share_by_note_id(note_id):
    db = get_share_db()
    return db.list_by_index("note_id", index_value = note_id)

def count_share_to(to_user):
    check_not_empty(to_user, "count_share_to")
    db = get_share_db()
    return db.count_by_index("to_user", index_value = to_user)


def get_share_to(to_user, note_id):
    return get_share_by_note_and_to_user(note_id, to_user)

xutils.register_func("note.share_to", share_note_to)
xutils.register_func("note.delete_share", delete_share)
xutils.register_func("note.list_share_to", list_share_to)
xutils.register_func("note.get_share_to", get_share_to)
xutils.register_func("note.count_share_to", count_share_to)
xutils.register_func("note.list_share_by_note_id", list_share_by_note_id)