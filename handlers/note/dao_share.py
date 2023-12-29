# -*- coding:utf-8 -*-
# @author mark
# @since 2022/03/12 18:57:19
# @modified 2022/03/12 23:21:48
# @filename dao_share.py

import json
import xutils
from xnote.core import xauth, xconfig, xtables

from xutils import Storage
from xutils import dbutil
from xutils import logutil
import handlers.note.dao as note_dao
from handlers.note.dao import ShareTypeEnum, ShareInfoDO
from .dao import sort_notes, batch_query_list

def check_not_empty(value, method_name):
    if value == None or value == "":
        raise Exception("[%s] can not be empty" % method_name)

def args_convert_func(note_id, from_user, to_user):
    obj = Storage(note_id = note_id, from_user = from_user, to_user = to_user)
    return json.dumps(obj)

class NoteShareDao:
    db = xtables.get_table_by_name("share_info")
    user_dao = xauth.UserDao
    share_type = ShareTypeEnum.note_to_user.value

    @classmethod
    def get_by_note_and_to_user(cls, note_id, to_id):
        where = dict(share_type="note_to_user", target_id = int(note_id), to_id = to_id)
        return cls.db.select_first(where=where)
    
    @classmethod
    def delete_by_id(cls, id):
        return cls.db.delete(where=dict(id=id))

    @classmethod
    def share_note_to(cls, target_id=0, from_id=0, to_id=0):
        record = cls.get_by_note_and_to_user(note_id=target_id, to_id=to_id)
        if record != None:
            # 已经分享了
            return

        record = ShareInfoDO()
        record.share_type = cls.share_type
        record.target_id = target_id
        record.from_id = from_id
        record.to_id = to_id
        return cls.db.insert(**record)

    @classmethod
    def count(cls, to_id=0):
        where = dict(share_type = cls.share_type)
        if to_id != 0:
            where["to_id"] = to_id
        return cls.db.count(where=where)
    
    @classmethod
    def list(cls, target_id=0, to_id=0, offset=0, limit=20, order="id desc"):
        where = dict(share_type = cls.share_type)
        if to_id != 0:
            where["to_id"] = to_id
        if target_id != 0:
            where["target_id"] = target_id
        return cls.db.select(where=where, offset=offset, limit=limit, order=order)

def get_share_by_note_and_to_user(note_id=0, to_user=""):
    to_id = xauth.UserDao.get_id_by_name(to_user)
    return NoteShareDao.get_by_note_and_to_user(note_id, to_id=to_id)


@logutil.log_deco("share_note_to", log_args = True, args_convert_func = args_convert_func)
def share_note_to(note_id, from_user, to_user):
    from_id = xauth.UserDao.get_id_by_name(from_user)
    to_id = xauth.UserDao.get_id_by_name(to_user)
    return NoteShareDao.share_note_to(target_id=note_id, from_id=from_id, to_id=to_id)

@logutil.log_deco("delete_share", log_args = True)
def delete_share(note_id, to_user=""):
    record = get_share_by_note_and_to_user(note_id, to_user)
    if record != None:
        NoteShareDao.delete_by_id(record.id)

def list_share_to(to_user, offset = 0, limit = None, orderby = None):
    if limit is None:
        limit = xconfig.PAGE_SIZE

    to_id = xauth.UserDao.get_id_by_name(to_user)
    records = NoteShareDao.list(to_id=to_id, offset=offset, limit=limit, order="ctime desc")
    id_list = list(map(lambda x:x.target_id, records))
    notes = batch_query_list(id_list)
    return notes

def list_share_by_note_id(note_id):
    result = NoteShareDao.list(target_id = note_id)
    idset = set()
    for item in result:
        idset.add(item.to_id)
    user_name_dict = xauth.UserDao.batch_get_name_by_ids(ids=idset)
    for item in result:
        item.to_user = user_name_dict.get(item.to_id)
    return result

def count_share_to(to_user):
    to_id = xauth.UserDao.get_id_by_name(to_user)
    return NoteShareDao.count(to_id=to_id)


def get_share_to(to_user, note_id):
    return get_share_by_note_and_to_user(note_id, to_user)

xutils.register_func("note.share_to", share_note_to)
xutils.register_func("note.delete_share", delete_share)
xutils.register_func("note.list_share_to", list_share_to)
xutils.register_func("note.get_share_to", get_share_to)
xutils.register_func("note.count_share_to", count_share_to)
xutils.register_func("note.list_share_by_note_id", list_share_by_note_id)