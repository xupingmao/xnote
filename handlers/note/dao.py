# encoding=utf-8
# Created by xupingmao on 2017/04/16
# @modified 2022/03/16 19:07:21
# @filename dao.py

"""资料的DAO操作集合
DAO层只做最基础的数据库交互，不做权限校验（空校验要做），业务状态检查之类的工作

一些表的说明
note_full:<note_id>              = 笔记的内容，包含一些属性（部分属性比如访问时间、访问次数不是实时更新的）
note_index:<note_id>             = 笔记索引，不包含内容
note_tiny:<user>:<note_id>       = 用户维度的笔记索引
notebook:<user>:<note_id>        = 用户维度的笔记本(项目)索引
token:<uuid>                     = 用于链接分享的令牌
note_history:<note_id>:<version> = 笔记的历史版本
note_comment:<note_id>:<timeseq> = 笔记的评论
comment_index:<user>:<timeseq>   = 用户维度的评论索引
search_history:<id>  = 用户维度的搜索历史
note_public:<note_id>            = 公开的笔记索引
"""
import time
import os
from xnote.core import xconfig
import xutils
from xnote.core import xmanager
import logging
from xnote.core import xauth
from xnote.core import xtables
import pdb
import enum
from xutils import Storage
from xutils import dateutil, dbutil, textutil, fsutil
from xutils import cacheutil
from .dao_api import NoteDao
from . import dao_log
from xutils.db.dbutil_helper import new_from_dict
from xutils import lists
from web.db import SQLLiteral

def register_note_table(name, description, check_user=False, user_attr=None):
    dbutil.register_table(name, description, category="note",
                          check_user=check_user, user_attr=user_attr)
    
register_note_table("notebook", "笔记分组", check_user=True, user_attr="creator")
register_note_table("token", "用于分享的令牌")

NOTE_DAO = xutils.DAO("note")

_full_db = dbutil.get_table("note_full")
_search_history_db = dbutil.get_table("search_history")

_note_history_db = dbutil.get_hash_table("note_history")
_note_history_index_db = dbutil.get_hash_table("note_history_index")
_public_db = dbutil.get_table("note_public")
_token_db = dbutil.get_table("token")

DB_PATH = xconfig.DB_PATH
MAX_STICKY_SIZE = 1000
MAX_SEARCH_SIZE = 1000
MAX_SEARCH_KEY_LENGTH = 20
MAX_LIST_SIZE = 1000
DEFAULT_DATETIME = "1970-01-01 00:00:00"

# 排序的枚举
ORDER_BY_SET = set([
    "ctime_desc", "ctime_priority", 
    "name", "name_asc", "name_desc", "name_priority", 
    "hot_index", "hot_desc",
])

NOTE_ICON_DICT = {
    "group": "fa-folder",

    "post": "fa-file-word-o",  # 废弃
    "html": "fa-file-word-o",  # 废弃
    "gallery": "fa-photo",
    "list": "fa-list",
    "plan": "fa-calendar-check-o",

    # 表格类
    "csv": "fa-table",  # 废弃
    "table": "fa-table",  # 废弃
    "form": "fa-table",  # 开发中
}

class NoteLevelEnum(enum.Enum):
    """笔记等级"""
    archived = -1 # 归档
    normal = 0 # 普通
    sticky = 1 # 置顶

class NoteIndexDO(Storage):
    def __init__(self, **kw):
        self.id = 0
        self.name = ""
        self.creator = ""
        self.creator_id = 0
        self.type = ""
        self.ctime = dateutil.format_datetime()
        self.mtime = dateutil.format_datetime()
        self.dtime = DEFAULT_DATETIME
        self.parent_id = 0
        self.size = 0
        self.children_count = 0
        self.version = 0
        self.is_deleted = 0
        self.is_public = 0
        self.level = 0 # 等级 (-1)-归档 0-正常, 1-置顶
        self.tag_str = ""
        self.visit_cnt = 0
        self.update(kw)

    @staticmethod
    def from_dict(dict_value):
        return new_from_dict(NoteIndexDO, dict_value)
    
    def before_save(self, index_do):
        # type: (NoteDO) -> None
        tags = index_do.tags
        if tags == None:
            tags = []
        self.tag_str = " ".join(tags)

class NoteDO(Storage):
    def __init__(self):
        self.id = 0 # 笔记ID
        self.name = ""
        self.path = ""
        self.creator = ""
        self.creator_id = 0
        self.ctime = dateutil.format_datetime()
        self.mtime = dateutil.format_datetime()
        self.atime = dateutil.format_datetime()
        self.dtime = DEFAULT_DATETIME # 删除时间
        self.type = "md"
        self.category = "" # 废弃
        self.size = 0
        self.children_count = 0
        self.parent_id = 0 # 默认挂在根目录下
        self.content = ""
        self.data = ""
        self.is_deleted = 0 # 0-正常， 1-删除
        self.is_public = 0  # 0-不公开, 1-公开
        self.token = ""
        self.priority = 0 # (-1):归档, 0-正常, 1-置顶
        self.level = 0 # 等级 (-1):归档, 0-正常, 1-置顶
        self.visit_cnt = 0
        self.visited_cnt = 0
        self.orderby = ""
        # 热门指数
        self.hot_index = 0
        # 版本
        self.version = 0
        self.tags = []

        # 假的属性
        self.url = ""
        self.icon = ""
        self.show_edit = True
        self.badge_info = ""
        self.create_date = ""
        self.update_date = ""

    @classmethod
    def from_dict(cls, dict_value):
        result = NoteDO()
        result.update(dict_value)
        return result
    
    def before_save(self):
        remove_virtual_fields(self)

def remove_virtual_fields(note):
    del_dict_key(note, "url")
    del_dict_key(note, "icon")
    del_dict_key(note, "show_edit")
    del_dict_key(note, "create_date")
    del_dict_key(note, "badge_info")
    del_dict_key(note, "create_date")
    del_dict_key(note, "update_date")
    del_dict_key(note, "tag_info_list")


def format_note_id(id):
    return str(id)


def format_date(date):
    return dateutil.format_date(date)


class NoteIndexDao:
    db = xtables.get_table_by_name("note_index")

    @classmethod
    def insert(cls, note_do: NoteDO):
        # type: (NoteDO) -> int
        assert note_do.creator_id != 0
        index_do = NoteIndexDO()
        for key in index_do:
            index_do[key] = note_do.get(key)
        index_do.pop("id", None)
        index_do.before_save(note_do)
        return cls.db.insert(**index_do)
    
    @classmethod
    def update(cls, note_do: NoteDO):
        assert note_do.creator_id != 0
        index_do = NoteIndexDO()
        for key in index_do:
            value = note_do.get(key)
            if value != None:
                index_do[key] = value
        index_do.before_save(note_do)
        note_id = int(note_do.id)
        return cls.db.update(where=dict(id=note_id), **index_do)

    @classmethod
    def update_visit_cnt(cls, note_id=0, user_id=0, visit_cnt=0):
        # TODO 待定中: visit_cnt是记录所有的访问量还是当前用户的访问量
        return cls.db.update(where=dict(id=note_id, user_id=user_id), visit_cnt=visit_cnt)
    
    @classmethod
    def incr_visit_cnt(cls, note_id=0):
        if not cls.db.writable:
            return
        return cls.db.update(where=dict(id=note_id), visit_cnt=SQLLiteral("visit_cnt+1"))

    @classmethod
    def update_level(cls, note_id=0, level=0):
        return cls.db.update(where=dict(id=note_id), level=level, mtime=xutils.format_datetime())

    @classmethod
    def get_by_id(cls, id=0):
        note_id = int(id)
        first = cls.db.select_first(where=dict(id=note_id))
        if first != None:
            cls.compat_old(first)
        return first

    @classmethod
    def get_by_name(cls, creator_id=0, name=""):
        result = cls.db.select_first(where=dict(creator_id=creator_id, name=name))
        if result != None:
            result = NoteIndexDO(**result)
            cls.compat_old(result)
        return result

    @classmethod
    def compat_old(cls, item: NoteIndexDO):
        item.tags = item.tag_str.split()
        item.priority = item.level
        item.content = ""
        item.data = ""
        item.visited_cnt = item.visit_cnt
        item.orderby = ""
        item.category = ""
        item.hot_index = item.visit_cnt
        item.badge_info = ""
        item.show_next = False
        item.archived = (item.level<0)
        item.atime = DEFAULT_DATETIME
    
    @classmethod
    def fix_result(cls, result=[]):
        for item in result:
            cls.compat_old(item)
            build_note_info(item)
        return result
    
    @classmethod
    def fix_single_result(cls, result):
        if result == None:
            return
        cls.compat_old(result)
        build_note_info(result)
        return result

    @classmethod
    def get_by_id_list(cls, id_list=[]):
        if len(id_list) == 0:
            return []
        int_list = []
        for id_str in id_list:
            int_list.append(int(id_str))
        result = cls.db.select(where="id in $id_list", vars=dict(id_list=int_list))
        return cls.fix_result(result)
    
    @classmethod
    def list(cls, creator_id=0, parent_id=0, offset=0, limit=20, type=None, type_list=[], is_deleted=0, 
            level=None, date=None, date_start=None, date_end=None, name_like=None, query_root=False, order="id desc"):
        if order=="dtime_asc":
            order = "dtime"
        if order=="ctime_desc":
            order = "ctime desc"

        if type == "table":
            type = None
            type_list = ["csv", "table"]
        
        date_like = ""
        where = "1=1"
        if creator_id != 0:
            where += " AND creator_id=$creator_id"
        else:
            # TODO 这里还是有问题
            where += " AND is_public = 1"
        if parent_id != 0 and parent_id != None:
            where += " AND parent_id=$parent_id"
        if query_root:
            where += " AND parent_id=0"
        if type != None and type != "all":
            where += " AND type=$type"
        if level != None:
            where += " AND level=$level"
        if is_deleted != None:
            where += " AND is_deleted=$is_deleted"

        if date != None:
            date_like = date + "%"
            where += " AND ctime LIKE $date_like"
        if date_start != None:
            where += " AND ctime >= $date_start"
        if date_end != None:
            where += " AND ctime < $date_end"

        if name_like != None:
            where += " AND name LIKE $name_like"
        if len(type_list) > 0:
            where += " AND type IN $type_list"
        vars = dict(creator_id=creator_id, parent_id=parent_id, type=type, level=level, 
                    is_deleted=is_deleted, date_like=date_like, name_like=name_like, 
                    type_list=type_list, date_start=date_start, date_end=date_end)
        result = cls.db.select(where=where, vars=vars, offset=offset, limit=limit, order=order)
        return cls.fix_result(result)
    
    @classmethod
    def iter_batch(cls, creator_id=0, batch_size=20):
        where = "AND creator_id=$creator_id"
        vars = dict(creator_id=creator_id)
        for batch_records in cls.db.iter_batch(batch_size=batch_size, where = where, vars=vars):
            yield batch_records

    @classmethod
    def count(cls, creator_id=0, type=None, type_list=[], level=None, is_deleted=0, parent_id=0, is_not_group=False, query_root=False):
        if type == "table":
            type = None
            type_list = ["csv", "table"]
        where = "1=1"
        if creator_id != 0:
            where += " AND creator_id=$creator_id"
        if type != None and type != "all":
            where += " AND type=$type"
        if level != None:
            where += " AND level=$level"
        if is_deleted != None:
            where += " AND is_deleted=$is_deleted"
        if parent_id != 0:
            where += " AND parent_id = $parent_id"
        if is_not_group:
            where += " AND type != $group_type"
        if len(type_list)>0:
            where += " AND type IN $type_list"
        if query_root:
            where += " AND parent_id=0"
        
        vars = dict(creator_id=creator_id, type=type, level=level, is_deleted=is_deleted, 
        parent_id=parent_id, group_type="group", type_list=type_list)
        return cls.db.count(where=where, vars=vars)
    
    @classmethod
    def list_float_notes(cls, creator_id=0, offset=0, limit=20, order="id desc"):
        """查询漂浮的笔记"""
        where = "creator_id=$creator_id AND parent_id=0 AND type!=$group_type AND is_deleted=0"
        vars = dict(creator_id=creator_id, group_type="group")
        result = cls.db.select(where=where, vars=vars, offset=offset, limit=limit,order=order)
        return cls.fix_result(result)
    
    @classmethod
    def delete_by_id(cls, note_id=0):
        return cls.db.delete(where=dict(id=note_id))
    
    @classmethod
    def find_prev(cls, creator_id=0, parent_id=0, name=""):
        where_sql = "creator_id = $creator_id AND parent_id = $parent_id AND name < $name"
        vars = dict(creator_id=creator_id, parent_id=parent_id, name=name)
        result = cls.db.select_first(where=where_sql, vars=vars, order="name desc", limit=1)
        return cls.fix_single_result(result)
    
    @classmethod
    def find_next(cls, creator_id=0, parent_id=0, name=""):
        where_sql = "creator_id = $creator_id AND parent_id = $parent_id AND name > $name"
        vars = dict(creator_id=creator_id, parent_id=parent_id, name=name)
        result = cls.db.select_first(where=where_sql, vars=vars, order="name", limit=1)
        return cls.fix_single_result(result)

class ShareTypeEnum(enum.Enum):
    note_public = "note_public"
    note_to_user = "note_to_user"

class ShareInfoDO(Storage):
    def __init__(self):
        self.ctime = dateutil.format_datetime()
        # 分享类型 {note_public, note_to_user}
        self.share_type = ""
        self.target_id = 0
        self.from_id = 0
        self.to_id = 0
        self.visit_cnt = 0

class ShareInfoDao:
    db = xtables.get_table_by_name("share_info")

    @classmethod
    def insert(cls, share_info: ShareInfoDO):
        return cls.db.insert(**share_info)
    
    @classmethod
    def insert_ignore(cls, share_info: ShareInfoDO):
        share_type = share_info.share_type
        target_id = share_info.target_id

        old = cls.db.select_first(where=dict(share_type=share_type, target_id=target_id))
        if old == None:
            cls.insert(share_info)

    @classmethod
    def incr_visit_cnt(cls, target_id=0):
        if not cls.db.writable:
            return
        where = dict(target_id=target_id)
        cls.db.update(where=where, visit_cnt=SQLLiteral("visit_cnt + 1"))

    @classmethod
    def delete_by_target(cls, share_type="", target_id=0):
        return cls.db.delete(where=dict(share_type=share_type, target_id=target_id))

    @classmethod
    def list(cls, share_type="", offset=0, limit=20, order="id desc"):
        where=dict(share_type=share_type)
        result = cls.db.select(where=where, offset=offset,limit=limit,order=order)
        return result
    
    @classmethod
    def count(cls, share_type=""):
        where=dict(share_type=share_type)
        return cls.db.count(where=where)


def get_root(creator=None):
    if creator == None:
        creator = xauth.current_name()

    assert creator != None
    root = NoteDO()
    root.creator = creator
    root.name = "根目录"
    root.type = "group"
    root.parent_id = 0
    build_note_info(root)
    root.url = "/note/group"
    return root


def is_root_id(id):
    return id in (None, "", "0", 0)


def get_default_group():
    group = NoteDO()
    group.name = "默认分组"
    group.type = "group"
    group.id = 0
    group.parent_id = 0
    build_note_info(group)
    group.url = "/note/default"
    return group


def get_archived_group():
    group = NoteDO()
    group.name = "归档分组"
    group.type = "group"
    group.id = 0
    group.parent_id = 0
    group.content = ""
    group.priority = 0
    build_note_info(group)
    group.url = "/note/archived"
    return group

def get_note_public_table():
    return _public_db


def batch_query_dict(id_list):
    result = dict()
    index_list = NoteIndexDao.get_by_id_list(id_list)

    for note in index_list:
        note_id = note.id
        result[note_id] = note
        build_note_info(note)
    return result

batch_query = batch_query_dict

def batch_query_list(id_list):
    result = []
    index_list = NoteIndexDao.get_by_id_list(id_list)
    for note in index_list:
        build_note_info(note)
        result.append(note)
    return result


def sort_by_name(notes):
    notes.sort(key=lambda x: x.name)
    sort_by_priority(notes)


def sort_by_name_desc(notes):
    notes.sort(key=lambda x: x.name, reverse=True)
    sort_by_priority(notes)


def sort_by_name_priority(notes):
    sort_by_name(notes)
    sort_by_priority(notes)


def sort_by_mtime_desc(notes):
    notes.sort(key=lambda x: x.mtime, reverse=True)


def sort_by_ctime_desc(notes):
    notes.sort(key=lambda x: x.ctime, reverse=True)
    sort_by_priority(notes)


def sort_by_atime_desc(notes):
    notes.sort(key=lambda x: x.atime, reverse=True)


def sort_by_priority(notes):
    # 置顶笔记
    notes.sort(key=lambda x: x.priority, reverse=True)


def sort_by_default(notes):
    # 先按照名称排序
    sort_by_name(notes)

    # 置顶笔记
    sort_by_priority(notes)

    # 文件夹放在前面
    sort_by_type(notes)


def sort_by_ctime_priority(notes):
    # 先按照名称排序
    sort_by_ctime_desc(notes)

    # 置顶笔记
    sort_by_priority(notes)

    # 文件夹放在前面
    sort_by_type(notes)


def sort_by_type(notes):
    # 文件夹放在前面
    notes.sort(key=lambda x: 0 if x.type == "group" else 1)


def sort_by_type_mtime_desc(notes):
    sort_by_mtime_desc(notes)
    sort_by_type(notes)


def sort_by_type_ctime_desc(notes):
    sort_by_ctime_desc(notes)
    sort_by_type(notes)


def sort_by_dtime_desc(notes):
    notes.sort(key=lambda x: x.dtime, reverse=True)


def sort_by_dtime_asc(notes):
    notes.sort(key=lambda x: x.dtime)


def sort_by_hot_index(notes):
    notes.sort(key=lambda x: x.hot_index or 0, reverse=True)
    sort_by_priority(notes)

    for note in notes:
        note.badge_info = "热度(%d)" % note.hot_index

def sort_by_size_desc(notes):
    notes.sort(key=lambda x:x.size or 0, reverse=True)
    sort_by_priority(notes)
    
    for note in notes:
        note.badge_info = "%s" % note.size

SORT_FUNC_DICT = {
    "name": sort_by_name,
    "name_asc": sort_by_name,
    "name_desc": sort_by_name_desc,
    "name_priority": sort_by_name_priority,
    "mtime_desc": sort_by_mtime_desc,
    "ctime_desc": sort_by_ctime_desc,
    "ctime_priority": sort_by_ctime_priority,
    "atime_desc": sort_by_atime_desc,
    "type_mtime_desc": sort_by_type_mtime_desc,
    "type_ctime_desc": sort_by_type_ctime_desc,
    "dtime_desc": sort_by_dtime_desc,
    "dtime_asc": sort_by_dtime_asc,
    "hot_index": sort_by_hot_index,
    "hot_desc": sort_by_hot_index,
    "size_desc": sort_by_size_desc,
    "default": sort_by_default,
}


def sort_notes(notes, orderby="name"):
    if orderby is None:
        orderby = "name"

    sort_func = SORT_FUNC_DICT.get(orderby, sort_by_mtime_desc)
    build_note_list_info(notes, orderby)
    sort_func(notes)


def build_note_list_info(notes, orderby=None):
    for note in notes:
        build_note_info(note, orderby)


def build_note_info(note, orderby=None):
    if note is None:
        return None

    # note.url = "/note/view?id={}".format(note["id"])
    note.url = "/note/view/{}".format(note["id"])

    if note.priority is None:
        note.priority = 0

    if note.content is None:
        note.content = ''

    if note.data is None:
        note.data = ''
    # process icon
    note.icon = NOTE_ICON_DICT.get(note.type, "fa-file-text-o")
    note.id = int(note.id)

    if note.type in ("list", "csv"):
        note.show_edit = False

    if note.visited_cnt is None:
        note.visited_cnt = 0

    if note.orderby is None:
        note.orderby = "ctime_desc"

    if note.hot_index is None:
        note.hot_index = 0

    if note.ctime != None:
        note.create_date = format_date(note.ctime)

    if note.mtime != None:
        note.update_date = format_date(note.mtime)

    # 处理删除时间
    if note.is_deleted == 1 and note.dtime == None:
        note.dtime = note.mtime

    if orderby == "hot_index":
        note.badge_info = "热度: %s" % note.hot_index
    
    if orderby == "mtime_desc":
        note.badge_info = format_date(note.mtime)

    if orderby == "ctime_desc":
        note.badge_info = format_date(note.ctime)

    if note.badge_info in (None, ""):
        note.badge_info = note.create_date

    if note.type == "group":
        _build_book_default_info(note)

    from . import dao_tag
    dao_tag.handle_tag_for_note(note)

    return note


def _build_book_default_info(note):
    if note.children_count == None:
        note.children_count = 0


def convert_to_path_item(note):
    return Storage(name=note.name, url=note.url, id=note.id,
                   type=note.type, priority=note.priority, is_public=note.is_public)


@xutils.timeit(name="NoteDao.ListPath:leveldb", logfile=True)
def list_path(file, limit=5):
    assert file != None

    pathlist = []
    while file is not None:
        pathlist.insert(0, convert_to_path_item(file))
        file.url = "/note/%s" % file.id
        if len(pathlist) >= limit:
            break
        
        if str(file.id) == "0":
            break

        parent_id = str(file.parent_id)
        # 处理根目录
        if parent_id == "0":
            if file.type != "group":
                pathlist.insert(0, get_default_group())
            elif file.archived:
                pathlist.insert(0, get_archived_group())
            pathlist.insert(0, convert_to_path_item(get_root(file.creator)))
            break

        file = get_by_id(parent_id, include_full=False)
    return pathlist


def get_full_by_id(id):
    if isinstance(id, int):
        id = str(id)
    return _full_db.get_by_id(id)

@xutils.timeit(name="NoteDao.GetById:leveldb", logfile=True)
def get_by_id(id, include_full=True, creator=None):
    if id == "" or id is None:
        return None
    id = str(id)
    if id == "0":
        return get_root(creator)

    id_int = int(id)
    note_index = NoteIndexDao.get_by_id(id_int)
    if note_index != None:
        note_index = NoteDO.from_dict(note_index)

    if not include_full and note_index != None:
        build_note_info(note_index)
        return note_index

    note = get_full_by_id(id)
    if note != None:
        note = NoteDO.from_dict(note)
    
    if note and not include_full:
        del note.content
        del note.data

    if note != None and note_index != None:
        note.name = note_index.name
        note.mtime = note_index.mtime
        note.atime = note_index.atime
        note.size = note_index.size
        note.tags = note_index.tags
        note.parent_id = note_index.parent_id
        note.visited_cnt = note_index.visit_cnt
        note.visit_cnt = note_index.visit_cnt
        note.hot_index = note_index.hot_index
        note.children_count = note_index.children_count
        note.path = note_index.path
        note.level = note_index.level
        note.creator_id = note_index.creator_id

    build_note_info(note)
    return note

def get_by_id_creator(id, creator, db=None):
    note = get_by_id(id, creator=creator)
    if note and note.creator == creator:
        return note
    return None


def get_by_token(token):
    token_info = _token_db.get_by_id(token)
    if token_info != None and token_info.type == "note":
        return get_by_id(token_info.id)
    return None


def get_by_user_skey(user_name, skey):
    return None

def delete_note_skey(note):
    # 使用的是note_index的索引,不需要处理
    pass


def get_or_create_note(skey, creator, creator_id=0):
    """根据skey查询或者创建笔记
    @param {string} skey 笔记的特殊key，用户维度唯一
    @param {string} creator 笔记的创建者
    @throws {exception} 创建异常
    """
    assert creator_id != 0
    if skey is None or skey == "":
        return None
    skey = skey.replace("-", "_")

    note = get_by_user_skey(creator, skey)
    if note != None:
        return note

    # 检查笔记名称
    check_by_name(creator, skey)

    note_dict = NoteDO()
    note_dict.name = skey
    note_dict.skey = skey
    note_dict.creator = creator
    note_dict.creator_id = creator_id
    note_dict.content = ""
    note_dict.data = ""
    note_dict.type = "md"
    note_dict.sub_type = "log"
    note_dict.parent_id = 0

    note_id = create_note(note_dict)

    return get_by_id(note_id)


def create_note_base(note_dict, date_str=None, note_id=None):
    """创建笔记的基础部分，无锁"""
    # 真实的创建时间
    ctime0 = dateutil.format_datetime()
    note_dict["ctime0"] = ctime0
    note_dict["atime"] = ctime0
    note_dict["mtime"] = ctime0
    note_dict["ctime"] = ctime0
    note_dict["version"] = 1

    if note_id is not None:
        # 指定id创建笔记
        note_dict["id"] = note_id
        put_note_to_db(note_id, note_dict)
        # 创建日志
        add_create_log(note_dict)
        return note_id
    elif date_str is None or date_str == "":
        # 默认创建规则
        note_id = NoteIndexDao.insert(note_dict)
        note_dict["id"] = note_id
        put_note_to_db(note_id, note_dict)
        # 创建日志
        add_create_log(note_dict)
        return note_id
    else:
        # 指定日期创建
        date_str = date_str.replace(".", "-")
        if date_str == dateutil.format_date():
            # 当天创建的，保留秒级
            timestamp = int(time.time() * 1000)
        else:
            timestamp = int(dateutil.parse_date_to_timestamp(date_str) * 1000)

        note_dict["ctime"] = dateutil.format_datetime(timestamp/1000)
        note_id = NoteIndexDao.insert(note_dict)
        note_dict["id"] = note_id
        put_note_to_db(note_id, note_dict)

        # 创建日志
        add_create_log(note_dict)
        return note_id


def is_not_empty(value):
    return xutils.is_str(value) and value != ""


def create_note(note_dict, date_str=None, note_id=None, check_name=True):
    assert isinstance(note_dict, NoteDO)
    assert note_dict.creator_id != 0
    assert isinstance(note_dict.level, int)

    content = note_dict.content
    creator = note_dict.creator
    name = note_dict.name
    
    # 标签去重
    tags = note_dict.tags
    tags = lists.get_uniq_list(tags)
    note_dict.tags = tags
    
    assert is_not_empty(name), "笔记名称不能为空"

    if "parent_id" not in note_dict:
        note_dict["parent_id"] = 0
    if "priority" not in note_dict:
        note_dict["priority"] = 0
    if "data" not in note_dict:
        note_dict["data"] = ""

    with dbutil.get_write_lock(name):
        # 检查名称是否冲突
        if check_name:
            check_by_name(creator, name)

        # 创建笔记的基础信息
        note_id = create_note_base(note_dict, date_str, note_id)
    
    if content != "":
        # 如果内部不为空，创建一个历史记录
        add_history(note_id, note_dict.version, note_dict)

    # 更新分组下面页面的数量
    update_children_count(note_dict.parent_id)

    # 创建对应的文件夹
    if type == "gallery":
        dirname = os.path.join(xconfig.UPLOAD_DIR, creator, str(note_id))
        xutils.makedirs(dirname)

    # 处理标签
    if tags != None and len(tags) > 0:
        from . import dao_tag
        dao_tag.TagBindDao.bind_tag(user_name = creator, note_id = note_id, tags=tags)

    # 最后发送创建笔记成功的消息
    create_msg = dict(name=name, type=type, id=note_id)
    xmanager.fire("note.add", create_msg)
    xmanager.fire("note.create", create_msg)

    return note_id


def create_token(type, note_id=""):
    uuid = textutil.generate_uuid()
    token_info = Storage(type=type, id=note_id)
    dbutil.put("token:%s" % uuid, token_info)
    return uuid

def check_and_create_default_book(user_name="", default_book_name="默认笔记本"):
    """检查并且创建默认笔记本"""
    assert user_name != None
    creator_id = xauth.UserDao.get_id_by_name(user_name)
    
    with dbutil.get_write_lock():
        result = NoteIndexDao.get_by_name(creator_id=creator_id, name=default_book_name)
        if result == None:
            default_book = NoteDO()
            default_book.ctime = dateutil.format_datetime()
            default_book.mtime = dateutil.format_datetime()
            default_book.name = default_book_name
            default_book.content = ""
            default_book.creator = user_name
            default_book.creator_id = creator_id
            default_book.is_public = 0
            default_book.type = "group"
            default_book.priority = 1
            default_book.children_count = 0
            default_book.size = 0
            default_book.is_deleted = 0
            default_book_id = create_note(default_book, check_name=False)
        else:
            note_info = result
            default_book_id = note_info.id
            update_kw = NoteDO()
            update_kw.type = "group"
            update_kw.priority = 1
            update_kw.is_public = 0
            update_kw.children_count = 0
            update_kw.is_deleted = 0
            update_kw.size = 0

            update_note(default_book_id, **update_kw)
        
        for note in list_default_notes(user_name):
            move_note(note, default_book_id)
    
        return default_book_id

def add_create_log(note):
    dao_log.add_create_log(note.creator, note)


def add_visit_log(user_name, note):
    dao_log.add_visit_log(user_name, note)


def put_note_to_db(note_id, note):
    assert isinstance(note, NoteDO)
    assert note.creator_id != 0
    
    creator = note.creator
    # 增加编辑日志
    dao_log.add_edit_log(creator, note)

    # 删除不需要持久化的数据
    remove_virtual_fields(note)

    # 保存到DB
    _full_db.put_by_id(note_id, note)

    # 更新索引
    update_index(note)

def touch_note(note_id):
    if is_root_id(note_id):
        return

    note = get_by_id(note_id)
    if note != None:
        note.mtime = dateutil.format_datetime()
        update_index(note)


def del_dict_key(dict, key):
    if key in dict:
        del dict[key]


def convert_to_index(note):
    note_index = Storage(**note)

    # 删除虚拟字段
    remove_virtual_fields(note_index)

    # 删除内容字段
    del_dict_key(note_index, 'data')
    del_dict_key(note_index, 'content')

    note_index.parent_id = str(note_index.parent_id)

    return note_index


def update_index(note):
    """更新索引的时候也会更新用户维度的索引(note_tiny)"""
    id = note['id']

    if is_root_id(id):
        # 根目录，不需要更新
        return
    NoteIndexDao.update(note)

def update_note(note_id, **kw):
    # 这里只更新基本字段，移动笔记使用 move_note
    logging.info("update_note, note_id=%s, kw=%s", note_id, kw)

    parent_id = kw.get("parent_id")
    content = kw.get('content')
    data = kw.get('data')
    priority = kw.get('priority')
    name = kw.get("name")
    atime = kw.get("atime")
    is_public = kw.get("is_public")
    tags = kw.get("tags")
    orderby = kw.get("orderby")
    archived = kw.get("archived")
    size = kw.get("size")
    token = kw.get("token")
    visited_cnt = kw.get("visited_cnt")
    creator_id = kw.get("creator_id", 0)

    note = get_by_id(note_id)
    if note is None:
        raise Exception("笔记不存在,id=%s" % note_id)
    
    if parent_id != None and parent_id != note.parent_id:
        raise Exception(
            "[note.dao.update_note] can not update `parent_id`, please use `note.dao.move_note`")

    if content:
        note.content = content
    if data:
        note.data = data
    if priority != None:
        note.priority = priority
    if name:
        note.name = name
    if atime:
        note.atime = atime

    # 分享相关的更新
    if is_public != None:
        note.is_public = is_public
    if is_public == 1:
        note.share_time = dateutil.format_time()
    if is_public == 0:
        note.share_time = None

    if tags != None:
        note.tags = tags
    if orderby != None:
        note.orderby = orderby
    if archived != None:
        note.archived = archived
    if size != None:
        note.size = size
    if token != None:
        note.token = token
    if visited_cnt != None:
        note.visited_cnt = visited_cnt

    if note.version is None:
        note.version = 1

    old_version = note.version
    note.mtime = xutils.format_time()
    note.version += 1

    # 只修改优先级
    if len(kw) == 1 and kw.get('priority') != None:
        note.version = old_version
    # 只修改名称
    if len(kw) == 1 and kw.get('name') != None:
        note.version = old_version

    if creator_id != 0:
        note.creator_id = creator_id

    put_note_to_db(note_id, note)
    return 1


def move_note(note, new_parent_id):
    # type: (NoteDO, int) -> None
    new_parent_id = int(new_parent_id)

    old_parent_id = note.parent_id
    note.parent_id = new_parent_id

    if old_parent_id == new_parent_id:
        return
    
    new_parent = get_by_id(new_parent_id)
    
    if new_parent != None:
        parent_path = new_parent.path or new_parent.name
        assert parent_path != None
        note.path = parent_path + " - " + note.name
    
    # 没有更新内容，只需要更新索引数据
    note.mtime = dateutil.format_datetime()
    update_index(note)

    # 更新文件夹的容量
    update_children_count(old_parent_id)
    update_children_count(new_parent_id, parent_note=new_parent)

def update0(note):
    """更新基本信息，比如name、mtime、content、items、priority等,不处理parent_id更新"""
    current = get_by_id(note.id)
    if current is None:
        return
    # 更新各种字段
    current_time = xutils.format_datetime()
    note.version = current.version + 1
    note.mtime = current_time
    note.atime = current_time
    put_note_to_db(note.id, note)


def get_by_name(creator, name):
    assert creator != None, "get_by_name:creator is None"
    assert name != None, "get_by_name: name is None"
    creator_id = xauth.UserDao.get_id_by_name(creator)
    note = NoteIndexDao.get_by_name(creator_id=creator_id, name=name)
    if note != None:
        return get_by_id(note.id)
    return None


def check_by_name(creator, name):
    note_by_name = get_by_name(creator, name)
    if note_by_name != None:
        raise Exception("笔记【%s】已存在" % name)


def visit_note(user_name, id):
    note = get_by_id(id)
    if note is None:
        return

    note.atime = xutils.format_datetime()
    # 访问的总字数
    if note.visited_cnt is None:
        note.visited_cnt = 0
    note.visited_cnt += 1
    note.visit_cnt = note.visited_cnt

    # 全局访问热度
    if note.hot_index is None:
        note.hot_index = 0
    note.hot_index += 1

    add_visit_log(user_name, note)

    # TODO 延迟更新索引
    # update_index(note)
    NoteIndexDao.incr_visit_cnt(note.id)

def visit_public(note_id):
    ShareInfoDao.incr_visit_cnt(target_id=note_id)

def update_children_count(parent_id, db=None, parent_note=None):
    print(f"update_children_count({parent_id})")

    if is_root_id(parent_id):
        return

    if parent_note == None:
        parent_note = get_by_id(parent_id)
    
    if parent_note is None:
        return

    creator_id = parent_note.creator_id
    count = 0
    children_items = list_by_parent(creator_id=creator_id, parent_id=parent_id)
    
    print(f"len(children_items)={len(children_items)}")

    for child in children_items:
        if child.type == "group":
            count += child.children_count
        else:
            count += 1

    parent_note.children_count = count
    update_index(parent_note)


def fill_parent_name(files):
    id_list = []
    for item in files:
        build_note_info(item)
        id_list.append(item.parent_id)

    note_dict = batch_query_dict(id_list)
    for item in files:
        parent = note_dict.get(item.parent_id)
        if parent != None:
            item.parent_name = parent.name
        else:
            item.parent_name = None


def check_group_status(status):
    if status is None:
        return
    if status not in ("all", "active", "archived"):
        raise Exception("[check_group_status] invalid status: %s" % status)


@xutils.timeit(name="NoteDao.ListGroup:leveldb", logfile=True)
def list_group_with_count(creator=None,
               orderby="mtime_desc",
               skip_archived=False,
               status="all", **kw):
    """查询笔记本列表"""

    offset = kw.get("offset", 0)
    limit = kw.get("limit", 1000)
    parent_id = kw.get("parent_id")
    category = kw.get("category")
    tags = kw.get("tags")
    search_name = kw.get("search_name")
    count_total = kw.get("count_total", False)
    count_only = kw.get("count_only", False)
    creator_id = kw.get("creator_id", 0)
    query_root = kw.get("query_root", False)

    if creator == None and creator_id == 0:
        raise Exception("creator和creator_id不能同时为空")
    
    check_group_status(status)
    if creator_id == 0:
        assert isinstance(creator, str)
        creator_id = xauth.UserDao.get_id_by_name(creator)

    q_tags = tags
    if tags != None and len(tags) == 0:
        q_tags = None

    q_name = search_name
    if q_name == "":
        q_name = None

    if q_name != None:
        q_name = q_name.lower()
    
    if category == "all":
        category = None

    def filter_group_func(value):
        # print(f"note_id={value.id}, archived={value.archived}")

        if skip_archived and value.archived:
            return False
        
        if q_tags != None:
            if not isinstance(value.tags, list):
                return False
            if not textutil.contains_any(value.tags, q_tags):
                return False

        if q_name != None:
            if q_name not in value.name.lower():
                return False
        
        if category != None and value.category != category:
            return False
        
        if status == "archived":
            return value.archived

        if status == "active":
            return not value.archived

        return True
    
    where_dict = dict(
        creator_id=creator_id,
        type="group",
        parent_id=parent_id,
        query_root=query_root,
    )

    notes = NoteIndexDao.list(
        **where_dict, limit=limit)

    notes = list(filter(filter_group_func, notes))
    
    if count_only:
        # TODO 其他筛选条件
        return [],len(notes)

    
    sort_notes(notes, orderby)
    result = notes[offset:offset + limit]

    if count_total:
        if len(notes) < limit:
            return result, len(notes)
        return result, len(notes)
    else:
        return result, 0


def list_group(*args, **kw):
    """@deprecated 废弃的方法, 替代方法
    - list_group_v2
    - list_group_with_count
    """
    list, count = list_group_with_count(*args, **kw)
    if kw.get("count_only") == True:
        return count
    if kw.get("count_total") == True:
        return list, count
    return list

def list_group_v2(*args, **kw):
    """查询笔记本列表"""
    list, count = list_group_with_count(*args, **kw)
    return list

@cacheutil.kw_cache_deco(prefix="note.count_group")
def count_group(creator, status=None, query_root=False):
    check_group_status(status)
    value = count_group_by_db(creator, status, query_root=query_root)
    return value


def count_group_by_db(creator, status=None, query_root=False):
    if status is None:
        creator_id = xauth.UserDao.get_id_by_name(creator)
        return NoteIndexDao.count(creator_id=creator_id, type="group", query_root=query_root)

    data, count = list_group_with_count(creator, status = status, count_only=True, query_root=query_root)
    return count


@xutils.timeit(name="NoteDao.ListRootGroup:leveldb", logfile=True)
def list_root_group(creator=None, orderby="name"):
    creator_id = xauth.UserDao.get_id_by_name(creator)
    notes = NoteIndexDao.list(creator_id=creator_id, parent_id=0, type="group")
    sort_notes(notes, orderby)
    return notes


def list_default_notes(creator, offset=0, limit=1000, orderby="mtime desc"):
    creator_id = xauth.UserDao.get_id_by_name(creator)
    notes = NoteIndexDao.list_float_notes(creator_id=creator_id, offset=offset, limit=limit)
    sort_notes(notes, orderby)
    return notes[offset:offset+limit]


def list_public(offset, limit, orderby="ctime_desc"):
    order="id desc"
    if orderby == "hot":
        order = "visit_cnt desc"
    else:
        order = "ctime desc"

    public_notes = ShareInfoDao.list(share_type="note_public", offset=offset,limit=limit,order=order)
    note_ids = []
    for note in public_notes:
        note_ids.append(note.target_id)

    batch_result = batch_query_dict(note_ids)
    
    # print("batch_result: ", batch_result)

    result = []
    for share_info in public_notes:
        note_info = batch_result.get(share_info.target_id)
        if note_info == None:
            logging.warning("笔记已删除:%s", share_info)
        else:
            note_info.url = "/note/view/public?id=%s" % note_info.id
            if orderby == "hot":
                note_info.badge_info = share_info.visit_cnt
            else:
                note_info.badge_info = dateutil.format_date(share_info.ctime)
            result.append(note_info)
    return result


def count_public():
    return ShareInfoDao.count(share_type="note_public")


@xutils.timeit_deco(name="NoteDao.ListNote:leveldb", logfile=True, logargs=True)
def list_by_parent(creator="", parent_id=None, offset=0, limit=1000,
                   orderby="name",
                   skip_group=False,
                   include_public=True,
                   *,
                   creator_id=0,
                   tags=None):
    """通过父级节点ID查询笔记列表"""
    if parent_id is None:
        raise Exception("list_by_parent: parent_id is None")

    if creator_id == 0:
        creator_id = xauth.UserDao.get_id_by_name(creator)

    # 只要一个标签匹配即可
    q_tags = tags
    if q_tags != None and len(q_tags) == 0:
        q_tags = None

    parent_id_int = int(parent_id)
    parent_id = str(parent_id)

    def filter_note_func(value):
        if skip_group and value.type == "group":
            return False

        if q_tags != None:
            if value.tags == None:
                return False
            if not textutil.contains_any(value.tags, q_tags):
                return False
        return True
    
    # TODO 优化其他筛选条件
    notes = NoteIndexDao.list(parent_id=parent_id_int, offset=offset, limit=1000, creator_id=creator_id)
    build_note_list_info(notes, orderby=orderby)
    notes = list(filter(filter_note_func, notes))
    if orderby == "db":
        note = get_by_id_creator(parent_id, creator)
        if note == None:
            raise Exception("笔记不存在:%s" % parent_id)
        orderby = note.orderby

    sort_notes(notes, orderby)
    return notes[offset:offset+limit]


def list_by_date(field, creator, date, orderby="ctime desc"):
    user = creator
    if user is None:
        user = "public"

    creator_id = xauth.UserDao.get_id_by_name(creator)
    files = NoteIndexDao.list(creator_id=creator_id, date=date, order=orderby)
    fill_parent_name(files)
    sort_notes(files, orderby)
    return files


@xutils.timeit(name="NoteDao.CountNote", logfile=True, logargs=True, logret=True)
def count_by_creator(creator):
    creator_id = xauth.UserDao.get_id_by_name(creator)
    return NoteIndexDao.count(creator_id=creator_id, is_not_group=True)


def count_user_note(creator):
    return count_by_creator(creator)


def count_ungrouped(creator):
    return count_by_parent(creator, 0)


@xutils.timeit(name="NoteDao.CountNoteByParent", logfile=True, logargs=True, logret=True)
def count_by_parent(creator, parent_id):
    """统计笔记数量
    @param {string} creator 创建者
    @param {string|number} parent_id 父级节点ID
    """
    creator_id = xauth.UserDao.get_id_by_name(creator)
    return NoteIndexDao.count(creator_id=creator_id, parent_id=parent_id)


@xutils.timeit(name="NoteDao.CountDict", logfile=True, logargs=True, logret=True)
def count_dict(user_name):
    import xtables
    return xtables.get_dict_table().count()


@xutils.timeit(name="NoteDao.FindPrev", logfile=True)
def find_prev_note(note, user_name):
    assert isinstance(note, NoteDO)
    parent_id = int(note.parent_id)
    return NoteIndexDao.find_prev(creator_id=note.creator_id, name = note.name, parent_id=parent_id)


@xutils.timeit(name="NoteDao.FindNext", logfile=True)
def find_next_note(note, user_name):
    assert isinstance(note, NoteDO)
    parent_id = int(note.parent_id)
    return NoteIndexDao.find_next(creator_id=note.creator_id, name = note.name, parent_id=parent_id)

class NoteHistoryIndexDO(xutils.Storage):
    def __init__(self, **kw):
        self.note_id = 0
        self.name = ""
        self.version = 0
        self.mtime = DEFAULT_DATETIME
        self.update(kw)

def add_history_index(note_id, version, new_note):
    brief = NoteHistoryIndexDO()
    brief.note_id = note_id
    brief.name = new_note.get("name")
    brief.version = version
    brief.mtime = new_note.get("mtime")

    version_str = str(version)
    _note_history_index_db.with_user(str(note_id)).put(version_str, brief)

def add_history(note_id, version, new_note):
    # type: (int, int, dict) -> None
    """version是新的版本"""
    assert version != None

    # 先记录索引
    add_history_index(note_id, version, new_note)

    version_str = str(version)
    note_copy = dict(**new_note)
    note_copy['note_id'] = note_id
    _note_history_db.with_user(str(note_id)).put(version_str, note_copy)

def list_history(note_id, limit=1000):
    """获取笔记历史的列表"""
    result_list = _note_history_index_db.with_user(str(note_id)).list(limit=limit, reverse = True)
    history_list = [y for x,y in result_list]
    history_list = sorted(
        history_list, key=lambda x: x.mtime or "", reverse=True)
    return history_list

def delete_history(note_id, version=None):
    pass


def get_history(note_id, version):
    """获取笔记历史的详情"""
    note_id = str(note_id)
    version_str = str(version)
    return _note_history_db.with_user(note_id).get(version_str)


def search_name(words, creator="", parent_id=0, orderby="hot_index", limit=1000):
    # TODO 搜索排序使用索引
    assert isinstance(words, list)

    words = [word.lower() for word in words]

    name_like = ""
    if len(words) > 0:
        name_like = "%" + "%".join(words) + "%"
    
    creator_id = xauth.UserDao.get_id_by_name(creator)
    result = NoteIndexDao.list(creator_id=creator_id, parent_id=parent_id, limit=limit, 
                               name_like=name_like)

    # 补全信息
    build_note_list_info(result)

    # 对笔记进行排序
    sort_notes(result, orderby)
    sort_by_priority(result)
    return result


def search_content(words, creator="", orderby="hot_index", limit=1000):
    # TODO 全文搜索排序使用索引
    assert isinstance(words, list)
    words = [word.lower() for word in words]

    def is_match(value):
        if value.content is None:
            return False
        return (value.creator == creator or value.is_public) \
            and textutil.contains_all(value.content.lower(), words)

    creator_id = xauth.UserDao.get_id_by_name(creator)
    result = []

    for index_list in NoteIndexDao.iter_batch(creator_id=creator_id, batch_size=20):
        id_list = [str(x.id) for x in index_list]
        batch_result = _full_db.batch_get_by_id(id_list)
        for key in batch_result:
            value = batch_result[key]
            if is_match(value):
                value.content = ""
                value.data = ""
                result.append(value)
            if len(result) > limit:
                break

    # 补全信息
    build_note_list_info(result)

    # 对笔记进行排序
    sort_notes(result, orderby)
    return result


def search_public(words):
    assert isinstance(words, list)
    words = [word.lower() for word in words]

    def search_public_func(key, value):
        if value.content is None:
            return False
        if not value.is_public:
            return False
        return textutil.contains_all(value.name.lower(), words)
    result = _full_db.list(filter_func=search_public_func,
                           offset=0, limit=MAX_SEARCH_SIZE)
    notes = [build_note_info(item) for item in result]
    sort_notes(notes)
    return notes

def count_removed(creator):
    creator_id = xauth.UserDao.get_id_by_name(creator)
    return NoteIndexDao.count(creator_id=creator_id, is_deleted=1)


def list_removed(creator, offset, limit, orderby="ctime desc"):
    creator_id = xauth.UserDao.get_id_by_name(creator)
    notes = NoteIndexDao.list(is_deleted=1, creator_id=creator_id, order=orderby)
    return notes[offset: offset + limit]


def document_filter_func(key, value):
    return value.type in ("md", "text", "html", "post", "log", "plan") and value.is_deleted == 0


def table_filter_func(key, value):
    return value.type in ("csv", "table") and value.is_deleted == 0


def get_filter_func(type, default_filter_func):
    if type == "document" or type == "doc":
        return document_filter_func
    if type in ("csv", "table"):
        return table_filter_func
    return default_filter_func


def list_by_type(creator, type, offset=0, limit=20, orderby="name desc", skip_archived=False):
    """按照类型查询笔记列表
    @param {str} creator 笔记作者
    @param {str|None} type  笔记类型
    @param {int} offset 下标
    @param {int} limit 返回的最大列数
    @param {str} orderby 排序
    @param {bool} skip_archived 是否跳过归档笔记
    """

    assert type != None, "note.dao.list_by_type: type is None"
    creator_id = xauth.UserDao.get_id_by_name(creator)
    notes = NoteIndexDao.list(creator_id=creator_id, offset=offset, limit=limit, type=type, order=orderby)
    sort_notes(notes, orderby)
    return notes


def count_by_type(creator, type):
    creator_id = xauth.UserDao.get_id_by_name(creator)
    return NoteIndexDao.count(creator_id=creator_id, type=type)


def count_sticky(creator):
    creator_id = xauth.UserDao.get_id_by_name(creator)
    return NoteIndexDao.count(creator_id=creator_id, level=1)



def list_sticky(creator, offset=0, limit=1000, orderby="ctime_desc"):
    creator_id = xauth.UserDao.get_id_by_name(creator)
    notes = NoteIndexDao.list(creator_id=creator_id, level=1, offset=offset, limit=limit)
    sort_notes(notes, orderby=orderby)
    return notes[offset:offset+limit]


def list_archived(creator, offset=0, limit=100):
    creator_id = xauth.UserDao.get_id_by_name(creator)
    notes = NoteIndexDao.list(creator_id=creator_id, level=-1)
    sort_notes(notes)
    return notes

class SearchHistory(Storage):

    def __init__(self) -> None:
        self.user = ""
        self.key = ""
        self.category = "default"
        self.cost_time = 0.0
        self.ctime = dateutil.format_datetime()

def add_search_history(user, search_key: str, category="default", cost_time=0.0):
    if user == None:
        user = "public"
    
    if len(search_key) > MAX_SEARCH_KEY_LENGTH:
        return
    
    expire_search_history(user)
    
    value = SearchHistory()
    value.user = user
    value.key = search_key
    value.category = category
    value.cost_time = cost_time

    return _search_history_db.insert(value, max_retry=100)


def list_search_history(user, limit=1000, orderby="time_desc"):
    if user is None or user == "":
        return []
    result = []
    for value in _search_history_db.list(limit = limit, reverse=True, where = dict(user=user)):
        if value.ctime == None:
            value.ctime = ""
        result.append(value)
    
    result.sort(key = lambda x:x.ctime, reverse = True)
    return result


def clear_search_history(user_name):
    assert user_name != None
    assert user_name != ""
    db = _search_history_db
    for item in db.list(where = dict(user=user_name), reverse=True, limit=1000):
        db.delete(item)

def expire_search_history(user_name, limit=1000):
    db = _search_history_db
    count = _search_history_db.count(where = dict(user = user_name))

    if count > limit:
        list_limit = min(20, count - limit)
        with dbutil.get_write_lock(user_name):
            obj_list = db.list(where = dict(user=user_name), limit = list_limit, reverse=False)
            db.batch_delete(obj_list)


class NoteStatDO(Storage):

    def __init__(self):
        self.total = 0
        self.group_count = 0
        self.doc_count = 0
        self.gallery_count = 0
        self.list_count = 0
        self.table_count = 0
        self.plan_count = 0
        self.log_count = 0
        self.sticky_count = 0
        self.removed_count = 0
        self.dict_count = 0
        self.comment_count = 0
        self.tag_count = 0
        self.update_time = 0.0

    def is_expired(self):
        expire_time = 60 * 60 # 1小时
        return time.time() - self.update_time > expire_time

    @classmethod
    def from_dict(cls, dict_value):
        result=NoteStatDO()
        result.update(dict_value)
        return result

@xutils.async_func_deco()
def refresh_note_stat_async(user_name):
    """异步刷新笔记统计"""
    refresh_note_stat(user_name)

@xutils.timeit_deco(name="NOTE_DAO:refresh_note_stat")
def refresh_note_stat(user_name):
    assert user_name != None, "[refresh_note_stat.assert] user_name != None"

    with dbutil.get_write_lock(user_name):
        stat = NoteStatDO()
        if user_name is None:
            return stat

        stat.total = count_by_creator(user_name)
        stat.group_count = count_group(user_name)
        stat.doc_count = count_by_type(user_name, "doc")
        stat.gallery_count = count_by_type(user_name, "gallery")
        stat.list_count = count_by_type(user_name, "list")
        stat.table_count = count_by_type(user_name, "table")
        stat.plan_count = count_by_type(user_name, "plan")
        stat.log_count = count_by_type(user_name, "log")
        stat.sticky_count = count_sticky(user_name)
        stat.removed_count = count_removed(user_name)
        stat.dict_count = count_dict(user_name)
        stat.comment_count = NoteDao.count_comment(user_name)
        stat.tag_count = NoteDao.count_tag(user_name)
        stat.update_time = time.time()

        dbutil.put("user_stat:%s:note" % user_name, stat)
        return stat

def get_empty_note_stat():
    stat = NoteStatDO()
    stat.total = 0
    stat.group_count = 0
    return stat


def get_note_stat(user_name):
    if user_name == None:
        return get_empty_note_stat()
    stat = dbutil.get("user_stat:%s:note" % user_name)
    if stat is None:
        stat = refresh_note_stat(user_name)
    else:
        stat = NoteStatDO.from_dict(stat)
        if stat.is_expired():
            stat = refresh_note_stat(user_name)
    if stat.tag_count == None:
        stat.tag_count = 0
    return stat


def get_gallery_path(note):
    from xnote.core import xconfig
    # 新的位置, 增加一级子目录（100个，二级子目录取决于文件系统
    # 最少的255个，最多无上限，也就是最少2.5万个相册，对于一个用户应该够用了）
    note_id = str(note.id)
    if len(note_id) < 2:
        second_dir = ("00" + note_id)[-2:]
    else:
        second_dir = note_id[-2:]
    standard_dir = os.path.join(
        xconfig.UPLOAD_DIR, note.creator, "gallery", second_dir, note_id)
    if os.path.exists(standard_dir):
        return standard_dir
    # TODO 归档的位置
    # 老的位置
    fpath = os.path.join(xconfig.UPLOAD_DIR, note.creator,
                         str(note.parent_id), note_id)
    if os.path.exists(fpath):
        # 修复数据另外通过工具实现
        return fpath

    # 如果依然不存在，创建一个地址
    fsutil.makedirs(standard_dir)
    return standard_dir

def get_virtual_group(user_name, name):
    if name == "ungrouped":
        creator_id = xauth.UserDao.get_id_by_name(user_name)
        files_count = NoteIndexDao.count(creator_id=creator_id, query_root=True, is_not_group=True)
        group = NoteDO()
        group.name = "未分类笔记"
        group.url = "/note/default"
        group.size = files_count
        group.children_count = files_count
        group.icon = "fa-folder"
        group.priority = 0
        return group
    else:
        raise Exception("[get_virtual_group] invalid name: %s" % name)


def check_not_empty(value, method_name):
    if value == None or value == "":
        raise Exception("[%s] can not be empty" % method_name)


# write functions
xutils.register_func("note.create", create_note)
xutils.register_func("note.update", update_note)
xutils.register_func("note.update0", update0)
xutils.register_func("note.move", move_note)
xutils.register_func("note.visit",  visit_note)
xutils.register_func("note.touch",  touch_note)
xutils.register_func("note.create_token", create_token)

# 内部更新索引的接口，外部不要使用
xutils.register_func("note.update_index", update_index)

# query functions
xutils.register_func("note.get_root", get_root)
xutils.register_func("note.get_default_group", get_default_group)
xutils.register_func("note.get_by_id", get_by_id)
xutils.register_func("note.get_by_token", get_by_token)
xutils.register_func("note.get_by_id_creator", get_by_id_creator)
xutils.register_func("note.get_by_name", get_by_name)
xutils.register_func("note.get_or_create", get_or_create_note)
xutils.register_func("note.get_virtual_group", get_virtual_group)
xutils.register_func("note.search_name", search_name)
xutils.register_func("note.search_content", search_content)
xutils.register_func("note.search_public", search_public)
xutils.register_func("note.batch_query_list", batch_query_list)

# list functions
xutils.register_func("note.list_path", list_path)
xutils.register_func("note.list_group", list_group)
xutils.register_func("note.list_default_notes", list_default_notes)
xutils.register_func("note.list_root_group", list_root_group)
xutils.register_func("note.list_by_parent", list_by_parent)
xutils.register_func("note.list_by_date", list_by_date)
xutils.register_func("note.list_by_type", list_by_type)
xutils.register_func("note.list_removed", list_removed)
xutils.register_func("note.list_sticky",  list_sticky)
xutils.register_func("note.list_archived", list_archived)
xutils.register_func("note.list_public", list_public)

# count functions
xutils.register_func("note.count_public", count_public)
xutils.register_func("note.count_recent_edit", count_user_note)
xutils.register_func("note.count_user_note", count_user_note)
xutils.register_func("note.count_ungrouped", count_ungrouped)
xutils.register_func("note.count_removed", count_removed)
xutils.register_func("note.count_by_type", count_by_type)
xutils.register_func("note.count_by_parent",  count_by_parent)
xutils.register_func("note.count_group", count_group)

# others
xutils.register_func("note.find_prev_note", find_prev_note)
xutils.register_func("note.find_next_note", find_next_note)

# history
xutils.register_func("note.add_history", add_history)
xutils.register_func("note.list_history", list_history)
xutils.register_func("note.get_history", get_history)
xutils.register_func("note.add_search_history", add_search_history)
xutils.register_func("note.list_search_history", list_search_history)
xutils.register_func("note.clear_search_history", clear_search_history)
xutils.register_func("note.expire_search_history", expire_search_history)

# stat
xutils.register_func("note.get_note_stat", get_note_stat)
xutils.register_func("note.get_gallery_path", get_gallery_path)
xutils.register_func("note.refresh_note_stat_async", refresh_note_stat_async)

NoteDao.get_by_id_creator = get_by_id_creator
NoteDao.get_root = get_root
NoteDao.batch_query_list = batch_query_list
NoteDao.get_note_stat = get_note_stat
