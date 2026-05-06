import xutils
import typing

from typing import List, Dict, Optional, Tuple, Sequence
from xnote.core import xtables
from .models import NoteDO, NoteIndexDO, NoteMetaRecord, OrderTypeEnum
from web.db import SQLLiteral
from xutils import dateutil

def format_date(date):
    return dateutil.format_date(date)



def _build_book_default_info(note: NoteIndexDO):
    if note.children_count == None:
        note.children_count = 0

def build_note_info(note: typing.Optional[NoteIndexDO], orderby=None, order_type=0):
    if note is None:
        return None

    note.compat_old()
    note.id = int(note.id)

    if note.type in ("list", "csv"):
        note.show_edit = False

    if note.order_type == 0:
        note.order_type = OrderTypeEnum.ctime_desc.int_value

    if note.ctime != None:
        note.create_date = format_date(note.ctime)

    if note.mtime != None:
        note.update_date = format_date(note.mtime)

    # 处理删除时间
    if note.is_deleted == 1 and note.dtime == None:
        note.dtime = note.mtime

    if orderby == "hot_index" or order_type == OrderTypeEnum.hot.int_value:
        note.badge_info = f"热度: {note.visit_cnt}"
    
    if orderby == "mtime_desc":
        note.badge_info = format_date(note.mtime)

    if orderby == "ctime_desc" or order_type == OrderTypeEnum.ctime_desc.int_value:
        note.badge_info = format_date(note.ctime)

    if note.badge_info in (None, ""):
        note.badge_info = format_date(note.ctime)

    if note.type == "group":
        _build_book_default_info(note)

    from . import dao_tag
    dao_tag.handle_tag_for_note(note)

    return note

def build_note_list_info(notes: Sequence[NoteIndexDO], orderby=None, order_type=0):
    for note in notes:
        build_note_info(note, orderby=orderby, order_type=order_type)


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
        new_id = cls.db.insert(**index_do)
        assert isinstance(new_id, int)
        return new_id
    
    @classmethod
    def update(cls, note_do: NoteIndexDO):
        assert note_do.creator_id != 0
        index_do = NoteIndexDO()
        for key in index_do:
            value = note_do.get(key)
            if value != None:
                index_do[key] = value
                
        if isinstance(note_do, NoteDO):
            index_do.before_save(note_do)
        
        note_id = int(note_do.id)
        return cls.db.update(where=dict(id=note_id), **index_do)

    @classmethod
    def update_visit_cnt(cls, note_id=0, user_id=0, visit_cnt=0):
        # TODO 待定中: visit_cnt是记录所有的访问量还是当前用户的访问量
        return cls.db.update(where=dict(id=note_id, user_id=user_id), visit_cnt=visit_cnt)
    
    @classmethod
    def incr_visit_cnt(cls, note_id=0, atime=None):
        if not cls.db.writable:
            return
        update_kw = {}
        if atime != None:
            update_kw["atime"] = atime
        update_kw["visit_cnt"] = SQLLiteral("visit_cnt+1")
        return cls.db.update(where=dict(id=note_id), **update_kw)

    @classmethod
    def update_level(cls, note_id=0, level=0):
        return cls.db.update(where=dict(id=note_id), level=level, mtime=xutils.format_datetime())
    
    @classmethod
    def touch(cls, note_id=0):
        if note_id == 0:
            return
        return cls.db.update(where=dict(id=note_id), mtime = dateutil.format_datetime())
    
    @classmethod
    def update_tags(cls, note_id: int, tags: List[str]):
        if note_id == 0:
            return
        
        tag_str = " ".join(tags)
        return cls.db.update(where=dict(id=note_id), tag_str = tag_str)
        
    @classmethod
    def get_by_id(cls, note_id=0, creator_id=0, check_user=False):
        if check_user:
            assert creator_id > 0
        
        note_id = int(note_id)
        where_sql = "id=$note_id"
        if creator_id > 0:
            where_sql += " AND creator_id=$creator_id"
        vars = dict(note_id=note_id, creator_id=creator_id)
        first = cls.db.select_first(where=where_sql, vars=vars)
        return cls.fix_single_result(first)
    
    @classmethod
    def get_note_name(cls, note_id=0, creator_id=0, check_user=False):
        note_index = cls.get_by_id(note_id=note_id, creator_id=creator_id, check_user=check_user)
        if note_index is None:
            return ""
        return note_index.name
    
    @classmethod
    def get_name_dict(cls, note_id_list=[]):
        where_sql = "id IN $note_id_list"
        vars = dict(note_id_list=note_id_list)
        result = cls.db.select(what="id, name", where=where_sql, vars=vars)
        notes = NoteIndexDO.from_dict_list(result)
        dict_result = {} # type: dict[int, str]
        for note in notes:
            dict_result[note.note_id] = note.name
        return dict_result

    @classmethod
    def get_by_name(cls, creator_id=0, name=""):
        result = cls.db.select_first(where=dict(creator_id=creator_id, name=name))
        if result != None:
            result = NoteIndexDO(**result)
            cls.compat_old(result)
        return result

    @classmethod
    def compat_old(cls, item: NoteIndexDO):
        item.compat_old()
    
    @classmethod
    def fix_result(cls, dict_list=[]):
        result = NoteIndexDO.from_dict_list(dict_list)
        for item in result:
            build_note_info(item)
        return result
    
    @classmethod
    def fix_single_result(cls, dict_value):
        # type: (dict|None) -> NoteIndexDO|None
        if dict_value == None:
            return
        result = NoteIndexDO.from_dict(dict_value)
        cls.compat_old(result)
        build_note_info(result)
        return result

    @classmethod
    def get_by_id_list(cls, id_list=[], creator_id=0):
        # type: (list[str|int], int) -> list[NoteIndexDO]
        if len(id_list) == 0:
            return []
        int_list = [int(id_str) for id_str in id_list]
        where_sql = "id in $id_list"
        if creator_id != 0:
            where_sql += " AND creator_id = $creator_id"
        db_result = cls.db.select(where=where_sql, vars=dict(id_list=int_list, creator_id=creator_id))
        result_list = cls.fix_result(db_result)
        result_dict = {} # type: dict[int, NoteIndexDO|None]
        for item in result_list:
            result_dict[item.note_id] = item
        result = [] # type: list[NoteIndexDO]
        for note_id in int_list:
            note_info = result_dict.get(note_id)
            if note_info != None:
                result.append(note_info)
        return result
    
    @classmethod
    def to_sql_order(cls, order=""):
        # dtime_asc -> dtime asc
        # ctime_desc -> ctime desc
        return order.replace("_", " ")

    @classmethod
    def list(cls, creator_id=0, parent_id=0, offset=0, limit=20, type=None, type_list=[], is_deleted=0, 
            level=None, date=None, date_start=None, date_end=None, date_end_exclusive=None, 
            exclude_types=[], name_like="", short_desc_like="", query_root=False, order="id desc"):
        order = cls.to_sql_order(order)

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
        if date_end_exclusive != None:
            where += " AND ctime < $date_end_exclusive"
        if name_like != "":
            where += " AND name LIKE $name_like"
        if short_desc_like != "":
            where += " AND manual_short_desc LIKE $short_desc_like"
        if len(type_list) > 0:
            where += " AND type IN $type_list"
        if len(exclude_types) > 0:
            where += " AND type NOT IN $exclude_types"

        vars = dict(creator_id=creator_id, parent_id=parent_id, type=type, level=level, 
                    is_deleted=is_deleted, date_like=date_like, name_like=name_like, 
                    type_list=type_list, date_start=date_start, date_end=date_end, 
                    date_end_exclusive=date_end_exclusive, exclude_types=exclude_types, 
                    short_desc_like=short_desc_like)
        result = cls.db.select(where=where, vars=vars, offset=offset, limit=limit, order=order)
        return cls.fix_result(result)
    
    @classmethod
    def iter_batch(cls, creator_id=0, batch_size=20):
        where = "AND creator_id=$creator_id"
        vars = dict(creator_id=creator_id)
        for batch_records in cls.db.iter_batch(batch_size=batch_size, where = where, vars=vars):
            yield NoteIndexDO.from_dict_list(batch_records)

    @classmethod
    def count(cls, creator_id=0, type=None, type_list=[], level=None, is_deleted=0, parent_id=0, 
              is_not_group=False, query_root=False, date_start=None, date_end_exclusive=None):
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
        if date_start != None:
            where += " AND ctime >= $date_start"
        if date_end_exclusive != None:
            where += " AND ctime < $date_end_exclusive"
        
        vars = dict(creator_id=creator_id, type=type, level=level, is_deleted=is_deleted, 
        parent_id=parent_id, group_type="group", type_list=type_list, 
        date_start=date_start, date_end_exclusive=date_end_exclusive)
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
    
    @classmethod
    def get_min_year(cls, creator_id=0):
        min_record = cls.db.select_first(what="ctime", where=dict(creator_id=creator_id, is_deleted=0), order="ctime", limit=1)
        if min_record != None:
            date_obj = dateutil.parse_date_to_object(min_record.ctime)
            return date_obj.year
        return -1
    
    @classmethod
    def get_max_year(cls, creator_id=0):
        min_record = cls.db.select_first(what="ctime", where=dict(creator_id=creator_id, is_deleted=0), order="ctime desc", limit=1)
        if min_record != None:
            date_obj = dateutil.parse_date_to_object(min_record.ctime)
            return date_obj.year
        return -1
    
    @classmethod
    def delete(cls, note_index:NoteIndexDO):
        return cls.db.delete(where=dict(id=note_index.note_id))
    
    @classmethod
    def update_field(cls, meta_info: NoteMetaRecord):
        now = dateutil.format_datetime()
        if meta_info.meta_key == "_create_date":
            time_obj = dateutil.parse_date_to_object(meta_info.meta_value)
            ctime = meta_info.meta_value + " " + time_obj.time_str
            cls.db.update(
                where=dict(id=meta_info.note_id, creator_id=meta_info.user_id), 
                ctime = ctime, 
                mtime = now)
            return
        
        if meta_info.meta_key == "_manual_short_desc":
            cls.db.update(
                where=dict(id=meta_info.note_id, creator_id=meta_info.user_id), 
                manual_short_desc = meta_info.meta_value,
                mtime = now)
            return
        
        raise Exception(f"invalid meta_key:{meta_info.meta_key}")
