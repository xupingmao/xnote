# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2023-09-09 11:04:21
@LastEditors  : xupingmao
@LastEditTime : 2023-12-24 16:10:11
@FilePath     : /xnote/xnote/service/service_tag.py
@Description  : 描述
"""
# encoding=utf-8
from xnote.core import xtables
from xutils import Storage, dateutil

class TagTypeEnum:
    """枚举无法扩展,所以这里不用,从外部添加枚举值可以直接设置新的属性"""
    empty = 0
    note_tag = 1 # 笔记标签
    msg_tag = 2  # 随手记标签

class TagBind(Storage):
    """标签绑定信息"""
    def __init__(self):
        self.ctime = dateutil.format_datetime()
        self.user_id = 0
        self.tag_type = 0
        self.tag_code = ""
        self.target_id = 0

    @classmethod
    def from_dict(cls, dict_value):
        if dict_value == None:
            return None
        bind = TagBind()
        bind.update(dict_value)
        return bind

    @classmethod
    def from_dict_list(cls, dict_list):
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
        self.tag_type = tag_type

    def get_by_target_id(self, user_id=0, target_id=0):
        results = self.db.select(where=dict(tag_type=self.tag_type, user_id=user_id, target_id=target_id))
        return TagBind.from_dict_list(results)

    def count_user_tag(self, user_id=0, tag_code = ""):
        tag_code = tag_code.lower()
        return self.db.count(where=dict(tag_type=self.tag_type, user_id=user_id, tag_code=tag_code))
    
    def normalize_tags(self, tags=[]):
        result = set()
        for tag in tags:
            if len(tag) > self.max_tag_length:
                continue
            result.add(tag.lower())
        return result

    def bind_tags(self, user_id=0, target_id=0, tags=[], update_only_changed = False):
        tags = self.normalize_tags(tags)
        
        where_dict = dict(tag_type=self.tag_type, user_id=user_id, target_id=target_id)
        
        if update_only_changed:
            old_tags = self.get_by_target_id(user_id=user_id, target_id=target_id)
            old_tag_set = set()
            for tag_info in old_tags:
                old_tag_set.add(tag_info.tag_code)
                
            if old_tag_set == tags:
                return
        
        with self.db.transaction():
            self.db.delete(where=where_dict)
            for tag_code in tags:
                new_bind = TagBind()
                new_bind.ctime = dateutil.format_datetime()
                new_bind.tag_type = self.tag_type
                new_bind.user_id = user_id
                new_bind.target_id = target_id
                new_bind.tag_code = tag_code
                self.db.insert(**new_bind)
