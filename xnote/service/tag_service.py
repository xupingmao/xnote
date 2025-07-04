# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-09-09 11:04:21
@LastEditors  : xupingmao
@LastEditTime : 2024-09-16 15:55:47
@FilePath     : /xnote/xnote/service/tag_service.py
@Description  : 描述
"""
# encoding=utf-8
import typing

from xutils import Storage, dateutil
from xnote.core import xtables
from xutils.base import BaseDataRecord, BaseEnum, EnumItem
from xutils import dateutil
from xutils import quote

class SystemTagEnum(BaseEnum):
    todo = EnumItem("待办", "$todo$")
    important = EnumItem("重要", "$1$")
    file = EnumItem("文件", "$file$")
    link = EnumItem("链接", "$link$")
    book = EnumItem("书籍", "$book$")
    people = EnumItem("人物", "$people$")
    phone = EnumItem("电话", "$phone$")

    _enums = [todo, important, file, link, book, people, phone]

    @staticmethod
    def is_sys_tag(tag_code=""):
        return SystemTagEnum.get_by_value(tag_code) != None
    
    @classmethod
    def get_name_by_code(cls, tag_code=""):
        for item in cls._enums:
            if item.value == tag_code:
                return item.name
        return tag_code
    
    @classmethod
    def to_tag_list(cls):
        result = [] # type: list[TagInfoDO]
        for item in cls._enums:
            result.append(TagInfoDO(tag_code=item.value, tag_name=item.name))
        return result

class TagTypeEnum(BaseEnum):
    """枚举无法扩展,所以这里不用,从外部添加枚举值可以直接设置新的属性"""
    note_tag = EnumItem("笔记标签", "1")
    msg_tag = EnumItem("随手记标签", "2")


class TagInfoDO(BaseDataRecord):
    def __init__(self, **kw):
        self.tag_id = 0
        self.ctime = xtables.DEFAULT_DATETIME
        self.mtime = xtables.DEFAULT_DATETIME
        self.user_id = 0
        self.tag_type = 0
        self.second_type = 0
        self.tag_code = ""
        self.tag_name = ""
        self.score = 0.0
        self.amount = 0
        self.visit_cnt = 0
        self.category_id = 0
        self.update(kw)

    def handle_from_dict(self):
        if self.tag_name == "":
            self.tag_name = SystemTagEnum.get_name_by_code(self.tag_code)

    def to_save_dict(self):
        result = dict(**self)
        result.pop("tag_id", None)
        result.pop("tag_name", None)
        return result
    
    @property
    def url(self):
        if self.tag_type == TagTypeEnum.msg_tag.int_value:
            if SystemTagEnum.is_sys_tag(self.tag_code):
                return f"/message/tag/list?tag=log.tags&sys_tag={self.tag_code}"
            return f"/message?tag=search&key={quote(self.tag_code)}"
        return f"/note/taginfo?tag_code={quote(self.tag_code)}"
    
    @property
    def tag_type_name(self):
        return TagTypeEnum.get_name_by_value(str(self.tag_type))
        

class TagBindDO(BaseDataRecord):
    """标签绑定信息, 业务唯一键=tag_type+tag_code+target_id"""
    def __init__(self):
        self.ctime = dateutil.format_datetime()
        self.user_id = 0
        self.tag_type = 0
        self.tag_code = ""
        self.target_id = 0    # target_id 对应的是 tag_type
        self.second_type = 0  # 二级类型, 这是target_id实体的一个属性
        self.sort_value = ""  # 排序字段

    @property
    def tag_name(self):
        return SystemTagEnum.get_name_by_code(self.tag_code)

TagBind = TagBindDO

class TagBindServiceImpl:
    """标签绑定服务"""
    db = xtables.get_table_by_name("tag_bind")
    max_tag_length = 30

    def __init__(self, tag_type = TagTypeEnum.note_tag.int_value):
        assert isinstance(tag_type, int)
        self.default_tag_type = tag_type
    
    def get_by_target_id(self, **kw):
        return self.list_by_target_id(**kw)
    
    def list_by_target_id(self, user_id=0, target_id=0, second_type=0):
        where_dict = dict(tag_type=self.default_tag_type, user_id=user_id, target_id=target_id)
        if second_type != 0:
            where_dict["second_type"] = second_type
        results = self.db.select(where=where_dict)
        return TagBind.from_dict_list(results)
    
    def get_page(self, user_id=0, target_id_list=[], tag_code="", offset=0, limit=20, skip_count=False, order=None):
        where_sql = "user_id=$user_id"
        if len(target_id_list) > 0:
            where_sql += " AND target_id in $target_id_list"
        if tag_code != "":
            where_sql += " AND tag_code=$tag_code"
        vars = dict(user_id=user_id, target_id_list=target_id_list, tag_code=tag_code)
        result = self.db.select(where=where_sql, vars=vars, offset=offset, limit=limit, order=order)
        count = 0
        if not skip_count:
            count = self.db.count(where=where_sql, vars=vars)
        
        return TagBind.from_dict_list(result), count
    
    def list_by_tag(self, user_id=0, tag_code="", second_type=0, offset=0, limit=20, order="sort_value desc"):
        tag_code = tag_code.lower()
        vars = dict(tag_type=self.default_tag_type, user_id=user_id, tag_code=tag_code, second_type=second_type)
        where_sql = "user_id = $user_id AND tag_code=$tag_code AND tag_type = $tag_type"
        if second_type != 0:
            where_sql += " AND second_type=$second_type"
        records = self.db.select(where=where_sql, vars=vars, offset=offset, limit=limit, order=order)
        return TagBind.from_dict_list(records)

    def count_user_tag(self, user_id=0, tag_code = "", target_id=0, second_type=0):
        if tag_code == "" and target_id == 0:
            raise Exception("tag_code and target_id can not be both empty")
        
        tag_code = tag_code.lower()
        vars = dict(tag_type=self.default_tag_type, second_type=second_type, user_id=user_id, tag_code=tag_code, target_id=target_id)
        where_sql = "user_id = $user_id AND tag_type=$tag_type"
        if tag_code != "":
            where_sql += " AND tag_code=$tag_code"
        if second_type != 0:
            where_sql += " AND second_type=$second_type"
        if target_id != 0:
            where_sql += " AND target_id=$target_id"
        return self.db.count(where_sql, vars=vars)
    
    def normalize_tags(self, tags=[]):
        result = set()
        for tag in tags:
            if len(tag) > self.max_tag_length:
                continue
            result.add(tag.lower())
        return result
    
    def get_tag_type(self, tag_type=0):
        if tag_type == 0:
            return self.default_tag_type
        return tag_type
    
    def update_second_type(self, user_id=0, target_id=0, second_type=0, sort_value=""):
        where_dict = {}
        where_dict["tag_type"] = self.default_tag_type
        where_dict["user_id"] = user_id
        where_dict["target_id"] = target_id

        self.db.update(where=where_dict, second_type=second_type, sort_value=sort_value)

    def bind_tags(self, user_id=0, target_id=0, tags=[], update_only_changed = False, second_type=0, sort_value=""):
        assert target_id > 0
        tags = self.normalize_tags(tags)
        tag_type = self.default_tag_type
        
        if update_only_changed:
            old_tags = self.get_by_target_id(user_id=user_id, target_id=target_id, second_type=second_type)
            old_tag_set = set()
            for tag_info in old_tags:
                old_tag_set.add(tag_info.tag_code)
                
            if old_tag_set == tags:
                return
        
        # 删除的条件不加 second_type
        where_dict = dict(tag_type=tag_type, user_id=user_id, target_id=target_id)

        with self.db.transaction():
            self.db.delete(where=where_dict)
            for tag_code in tags:
                new_bind = TagBind()
                new_bind.ctime = dateutil.format_datetime()
                new_bind.tag_type = tag_type
                new_bind.second_type = second_type
                new_bind.user_id = user_id
                new_bind.target_id = target_id
                new_bind.tag_code = tag_code
                new_bind.sort_value = sort_value
                self.db.insert(**new_bind)
    
    def delete_tags(self, user_id=0, target_id=0):
        where_sql = "user_id=$user_id AND target_id=$target_id"
        vars = dict(user_id=user_id, target_id=target_id)
        return self.db.delete(where=where_sql, vars=vars)

class TagInfoServiceImpl:

    db = xtables.get_table_by_name("tag_info")

    def __init__(self, tag_type=TagTypeEnum.note_tag.int_value) -> None:
        self.tag_type = tag_type

    def handle_tag_type(self, tag_type=0):
        if tag_type > 0:
            return tag_type
        return self.tag_type
    
    def _get_like_text(self, text=""):
        if not text.startswith("%"):
            text = "%" + text
        if not text.endswith("%"):
            text = text + "%"
        return text
    
    def get_page(self, user_id=0, tag_type=0, target_id_list=[], offset=0, limit=20, 
                 skip_count=False, skip_tag_type=False, order=None):
        where_sql = "user_id=$user_id"
        tag_type = self.handle_tag_type(tag_type)

        if not skip_tag_type and tag_type > 0:
            where_sql += " AND tag_type=$tag_type"
        if len(target_id_list) > 0:
            where_sql += " AND target_id IN $target_id_list"
        vars = dict(user_id=user_id, tag_type=tag_type, target_id_list=target_id_list)
        result = self.db.select(where=where_sql, vars=vars, offset=offset, limit=limit, order=order)
        if skip_count:
            count = 0
        else:
            count = self.db.count(where=where_sql, vars=vars)
        return TagInfoDO.from_dict_list(result), count
    
    def get_by_id(self, tag_id=0, user_id=0):
        where_dict = dict(tag_id=tag_id)
        if user_id > 0:
            where_dict["user_id"] = user_id
        result = self.db.select_first(where=where_dict)
        return TagInfoDO.from_dict_or_None(result)
    
    def get_by_code_list(self, user_id=0, tag_code_list=[], limit=1000, order=None) -> typing.List[TagInfoDO]:
        if len(tag_code_list) == 0:
            return []
        tag_type = self.handle_tag_type()
        where_sql = "user_id=$user_id AND tag_code in $tag_code_list AND tag_type = $tag_type"
        vars = dict(user_id=user_id, tag_code_list=tag_code_list, tag_type = tag_type)
        result = self.db.select(where=where_sql, vars=vars, limit=limit, order=order)
        return TagInfoDO.from_dict_list(result)
    
    def get_first(self, tag_id=0, tag_code="", user_id=0):
        where_sql = "user_id=$user_id"
        if tag_id > 0:
            where_sql += " AND tag_id=$tag_id"
        if tag_code != "":
            where_sql += " AND tag_code=$tag_code"
        vars = dict(tag_id=tag_id, user_id=user_id, tag_code=tag_code)
        result = self.db.select_first(where=where_sql, vars=vars)
        return TagInfoDO.from_dict_or_None(result)
    
    def search(self, user_id=0, tag_code_like="", offset=0, limit=20, order=None):
        where_sql = "user_id=$user_id AND tag_type=$tag_type AND tag_code LIKE $tag_code_like"
        tag_code_like = self._get_like_text(tag_code_like)
        tag_type = self.tag_type
        vars = dict(user_id=user_id, tag_code_like=tag_code_like, tag_type=tag_type)
        result = self.db.select(where=where_sql, vars=vars, offset=offset, limit=limit, order=order)
        return TagInfoDO.from_dict_list(result)
        
    def update(self, tag_info: TagInfoDO):
        assert tag_info.user_id > 0
        assert tag_info.tag_type > 0
        
        data = tag_info.to_save_dict()
        data.pop("ctime", None)
        return self.db.update(where=dict(tag_id=tag_info.tag_id), **data)
    
    def update_amount(self, user_id=0,  tag_code="", amount=0):
        tag_type = self.handle_tag_type()
        self.db.update(where=dict(user_id=user_id, tag_code=tag_code, tag_type=tag_type), amount=amount)
    
    def create(self, tag_info: TagInfoDO):
        tag_type = self.handle_tag_type(tag_info.tag_type)
        assert tag_info.user_id > 0
        assert tag_type > 0
        assert tag_info.tag_code != ""

        now = dateutil.format_datetime()
        tag_info.tag_type = tag_type
        tag_info.ctime = now
        tag_info.mtime = now
        data = tag_info.to_save_dict()
        return self.db.insert(**data)
    
    def save(self, tag_info: TagInfoDO):
        if tag_info.tag_id != 0:
            return self.update(tag_info)
        
        tag_code = tag_info.tag_code
        user_id = tag_info.user_id
        old = self.get_first(tag_code=tag_code, user_id=user_id)
        if old != None:
            tag_info.tag_id = old.tag_id
            return self.update(tag_info)
        return self.create(tag_info)
    
    def delete(self, tag_info: TagInfoDO):
        self.db.delete(where=dict(tag_id=tag_info.tag_id))

    def count(self, user_id=0):
        where_sql = "user_id=$user_id AND tag_type=$tag_type"
        vars = dict(tag_type=self.tag_type, user_id=user_id)
        return self.db.count(where=where_sql, vars=vars)

class TagCategoryDO(BaseDataRecord):

    def __init__(self, **kw):
        self.category_id = 0
        self.user_id = 0
        self.name = ""
        self.description = ""
        self.ctime = xtables.DEFAULT_DATETIME
        self.mtime = xtables.DEFAULT_DATETIME
        self.sort_order = 0
        self.tag_amount = 0
        self.update(kw)

    def to_save_dict(self):
        result = dict(**self)
        result.pop("category_id")
        return result

class TagCategoryServiceImpl:

    db = xtables.get_table_by_name("tag_category")

    def create(self, tag_category:TagCategoryDO):
        now = dateutil.format_datetime()
        tag_category.ctime = now
        tag_category.mtime = now
        save_dict = tag_category.to_save_dict()
        return self.db.insert(**save_dict)
    
    def save(self, category_info: TagCategoryDO):
        if category_info.category_id > 0:
            category_info.mtime = dateutil.format_datetime()
            save_dict = category_info.to_save_dict()
            return self.db.update(where=dict(category_id=category_info.category_id), **save_dict)
        else:
            return self.create(category_info)
    
    def list(self, user_id=0, limit=100):
        assert user_id > 0
        result_list = self.db.select(where=dict(user_id=user_id), limit=limit, order="sort_order")
        return TagCategoryDO.from_dict_list(result_list)
    
    def get_by_id(self, category_id=0, user_id=0):
        if category_id == 0:
            return None
        result = self.db.select_first(where=dict(category_id=category_id, user_id=user_id))
        return TagCategoryDO.from_dict_or_None(result)
    
    def get_by_name(self, name="", user_id=0):
        result = self.db.select_first(where=dict(name=name, user_id=user_id))
        return TagCategoryDO.from_dict_or_None(result)
    
    def get_name_dict(self, user_id=0, limit=100):
        assert user_id > 0
        result_list = self.db.select(what="category_id,name", where=dict(user_id=user_id), limit=limit)
        result = {} # type: dict[int, str]
        for item in TagCategoryDO.from_dict_list(result_list):
            result[item.category_id] = item.name
        return result

    def delete(self, category_info: TagCategoryDO):
        return self.db.delete(where=dict(category_id = category_info.category_id))

TagCategoryService = TagCategoryServiceImpl()
NoteTagInfoService = TagInfoServiceImpl(tag_type=TagTypeEnum.note_tag.int_value)
MsgTagInfoService = TagInfoServiceImpl(tag_type=TagTypeEnum.msg_tag.int_value)
TagInfoService = TagInfoServiceImpl(tag_type=0)

NoteTagBindService = TagBindServiceImpl(tag_type=TagTypeEnum.note_tag.int_value)
MsgTagBindService = TagBindServiceImpl(tag_type=TagTypeEnum.msg_tag.int_value)
