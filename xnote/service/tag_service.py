# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-09-09 11:04:21
@LastEditors  : xupingmao
@LastEditTime : 2024-07-13 15:31:27
@FilePath     : /xnote/xnote/service/tag_service.py
@Description  : 描述
"""
# encoding=utf-8
import typing

from xnote.core import xtables
from xutils import Storage, dateutil

class TagTypeEnum:
    """枚举无法扩展,所以这里不用,从外部添加枚举值可以直接设置新的属性"""
    empty = 0
    note_tag = 1 # 笔记标签
    msg_tag = 2  # 随手记标签

class TagBind(Storage):
    """标签绑定信息, 业务唯一键=tag_type+tag_code+target_id"""
    def __init__(self):
        self.ctime = dateutil.format_datetime()
        self.user_id = 0
        self.tag_type = 0
        self.tag_code = ""
        self.target_id = 0    # target_id 对应的是 tag_type
        self.second_type = 0  # 二级类型, 这是target_id实体的一个属性

    @classmethod
    def from_dict(cls, dict_value) -> typing.Optional["TagBind"]:
        if dict_value == None:
            return None
        bind = TagBind()
        bind.update(dict_value)
        return bind

    @classmethod
    def from_dict_list(cls, dict_list) -> typing.List["TagBind"]:
        result = []
        for item in dict_list:
            result.append(cls.from_dict(item))
        return result


class TagBindService:
    """标签绑定服务"""
    db = xtables.get_table_by_name("tag_bind")
    max_tag_length = 30

    def __init__(self, tag_type = TagTypeEnum.empty):
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
    
    def list_by_tag(self, user_id=0, tag_code="", second_type=0, offset=0, limit=20, order="ctime desc"):
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
    
    def update_second_type(self, user_id=0, target_id=0, second_type=0):
        where_dict = {}
        where_dict["tag_type"] = self.default_tag_type
        where_dict["user_id"] = user_id
        where_dict["target_id"] = target_id

        self.db.update(where=where_dict, second_type=second_type)

    def bind_tags(self, user_id=0, target_id=0, tags=[], update_only_changed = False, second_type=0):
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
                self.db.insert(**new_bind)
