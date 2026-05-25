# encoding=utf-8


import xutils
import typing
from xnote.core import xtables
from xutils import dateutil
from xutils import jsonutil
from xutils.base import BaseDataRecord

class CommentTypeEnum:
    """枚举无法扩展,所以这里不用,从外部添加枚举值可以直接设置新的属性"""
    empty = ""
    note = "note"
    list_item = "list_item"

class CommentIndexRecord(BaseDataRecord):
    def __init__(self):
        self.id = 0
        self.ctime = dateutil.format_datetime()
        self.mtime = dateutil.format_datetime()
        self.type = ""
        self.user_id = 0
        self.target_id = 0
        self.pin_level = 0
        self.parent_comment_id = 0

class CommentExtraData(BaseDataRecord):
    """评论额外数据"""
    def __init__(self, **kw):
        self.user = ""
        self.files = []
        self.ref_comment_id = 0  # 被回复的评论ID
        self.ref_user_id = 0     # 被回复的用户ID
        self.update(kw)
    
    def to_dict(self):
        return self.to_save_dict()
    
    @staticmethod
    def from_dict(extra_str):
        if extra_str == "" or extra_str is None:
            return CommentExtraData()
        try:
            extra_dict = jsonutil.from_json(extra_str)
            return CommentExtraData(**extra_dict)
        except:
            return CommentExtraData()

class CommentDataRecord(BaseDataRecord):
    _ignore_save_fields = ["_extra_data"]
    
    def __init__(self, **kw):
        self.id = 0
        self.create_time = 0
        self.update_time = 0
        self.version = 0
        self.type = ""
        self.user_id = 0
        self.target_id = 0
        self.pin_level = 0
        self.parent_comment_id = 0
        self.content = ""
        self.extra = ""
        self._extra_data = None  # 内存中的 ExtraData 对象，不存入数据库
        self.update(kw)
    
    @property
    def extra_data(self):
        if self._extra_data is None:
            self._extra_data = CommentExtraData.from_dict(self.extra)
        return self._extra_data

class CommentService:

    db = xtables.get_table_by_name("comment_index")
    data_db = xtables.get_table_by_name("comment_data")

    def __init__(self):
        pass
    
    def create(self, user_id=0, target_id=0, type="", parent_comment_id=0):
        now = dateutil.format_datetime()
        new_id = self.db.insert(ctime=now, mtime=now, type=type, user_id=user_id, target_id=target_id, parent_comment_id=parent_comment_id)
        assert isinstance(new_id, int)
        return new_id
    
    def create_data(self, record: CommentDataRecord):
        save_dict = record.to_save_dict()
        if record.id == 0:
            new_id = self.data_db.insert(**save_dict)
            record.id = new_id
        else:
            self.data_db.insert(**save_dict)
        return record.id
    
    def get_data_by_id(self, comment_id=0):
        result = self.data_db.select_first(where=dict(id=comment_id))
        return CommentDataRecord.from_dict_or_None(result)
    
    def update_data(self, record: CommentDataRecord, old_version=0):
        save_dict = record.to_save_dict()
        return self.data_db.update(**save_dict, where=dict(id=record.id, version=old_version))
    
    def delete_data_by_id(self, id=0):
        return self.data_db.delete(where=dict(id=id))
    
    def build_where(self, user_id: int=0, target_id: int=0, date: typing.Optional[str]=None, type: str="", parent_comment_id: typing.Optional[int]=None):
        date_like = date
        where = "1=1"
        if user_id != 0:
            where += " AND user_id = $user_id"
        if target_id != 0:
            where += " AND target_id = $target_id"
        if date != None and date != "":
            where += " AND ctime LIKE $date_like"
            date_like = date + "%"
        if type != "":
            where += " AND type=$type"
        if parent_comment_id is not None:
            where += " AND parent_comment_id = $parent_comment_id"
        
        vars = dict(type=type, user_id=user_id, target_id=target_id, date_like=date_like, parent_comment_id=parent_comment_id)
        return where, vars
    
    def list(self, user_id: int=0, target_id: int=0, date: typing.Optional[str]=None, type: str="", parent_comment_id: typing.Optional[int]=None, offset: int=0, limit: int=20, order: str="ctime desc", what: str="*"):
        if user_id ==0 and target_id == 0:
            raise Exception("user_id,target_id不能同时为0")
        
        where, vars = self.build_where(user_id=user_id, target_id=target_id,date=date,type=type,parent_comment_id=parent_comment_id)
        result = self.db.select(where=where, vars=vars, offset=offset,limit=limit,order=order)
        return CommentIndexRecord.from_dict_list(result)
    
    def list_iter(self, user_id: int=0, target_id: int=0, date: typing.Optional[str]=None, type: str="", batch_size: int=100, order: str="ctime desc"):
        """分批迭代查询评论索引
        
        使用迭代器分批获取数据，避免一次性加载大量数据到内存
        """
        if user_id == 0 and target_id == 0:
            raise Exception("user_id,target_id不能同时为0")
        
        offset = 0
        while True:
            idx_list = self.list(
                user_id=user_id, target_id=target_id, date=date, type=type,
                offset=offset, limit=batch_size, order=order
            )
            if not idx_list:
                break
            yield idx_list
            if len(idx_list) < batch_size:
                break
            offset += batch_size
    
    def get_by_id(self, comment_id: int=0, user_id: int=0):
        where_dict = dict(id = comment_id)
        if user_id > 0:
            where_dict["user_id"] = user_id
        result = self.db.select_first(where=where_dict)
        return CommentIndexRecord.from_dict_or_None(result)

    def count(self, user_id: int=0, target_id: int=0, date: typing.Optional[str]=None, type: str="", parent_comment_id: typing.Optional[int]=None):
        where, vars = self.build_where(user_id=user_id, target_id=target_id,date=date,type=type,parent_comment_id=parent_comment_id)
        return self.db.count(where=where, vars=vars)
    
    def delete_by_id(self, id=0):
        return self.db.delete(where=dict(id=id))
    
    def update_ctime(self, id=0, ctime=""):
        return self.db.update(where=dict(id=id), ctime=ctime)
    
    def update(self, index: CommentIndexRecord):
        save_dict = index.to_save_dict()
        return self.db.update(where=dict(id=index.id), **save_dict)
