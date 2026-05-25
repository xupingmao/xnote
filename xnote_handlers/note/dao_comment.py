# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/04 22:07:44
# @modified 2022/04/16 21:57:34
# @filename dao_comment.py
import xutils
import typing

from xnote.core import xconfig
from xnote.core import xmanager
from xnote.core import xauth
from xutils import textutil
from xutils import dateutil
from xutils import jsonutil
from xutils.db.dbutil_helper import PageBuilder
from xnote.service import CommentService, CommentIndexRecord, CommentDataRecord
from xutils.base import BaseDataRecord
from xutils.functions import is_empty

NOTE_DAO = xutils.DAO("note")

comment_service = CommentService()

class CommentVO(BaseDataRecord):
    def __init__(self, **kw):
        self.id = 0
        self.user = ""
        self.user_id = 0
        self.note_id = 0
        self.type = ""
        self.content = ""
        self.create_time = 0
        self.update_time = 0
        self.version = 0
        self.pin_level = 0
        self.files = []
        self.parent_comment_id = 0  # 父评论ID
        self.ref_comment_id = 0     # 被回复的评论ID
        self.ref_user_id = 0        # 被回复的用户ID
        self.reply_count = 0       # 回复数量
        self.ref_user = ""          # 被回复的用户名
        self.update(kw)

    def update_index(self, index: CommentIndexRecord):
        self.id = index.id
        self.user_id = index.user_id
        self.pin_level = index.pin_level

    @property
    def date(self):
        if self.create_time > 0:
            return dateutil.format_date(self.create_time / 1000)
        return ""
    
    @property
    def ctime_str(self):
        """显示完整的创建日期时间，精度为秒"""
        if self.create_time > 0:
            return dateutil.format_datetime(self.create_time / 1000)
        return ""

class CommentDao:

    valid_type_set = set(["", None, "list_item"])
    
    @classmethod
    def check(cls, comment: CommentVO):
        assert comment != None, "comment is None"
        assert comment.user != None, "comment.user is None"
        assert comment.type in cls.valid_type_set, "comment.type is invalid"
        assert comment.note_id != None
        if comment.content == "" and is_empty(comment.files):
            raise Exception("content or files is empty")
    
    @classmethod
    def create(cls, comment: CommentVO):
        assert isinstance(comment, CommentVO)
        cls.check(comment)
        comment.create_time = dateutil.timestamp_ms()
        comment.update_time = comment.create_time
        index_id = comment_service.create(type=comment.type, user_id=comment.user_id, target_id=int(comment.note_id), parent_comment_id=comment.parent_comment_id)
        comment.id = index_id
        
        # 保存到 comment_data 表
        data_record = CommentDataRecord()
        data_record.id = index_id
        data_record.create_time = comment.create_time
        data_record.update_time = comment.update_time
        data_record.type = comment.type
        data_record.user_id = comment.user_id
        data_record.target_id = int(comment.note_id)
        data_record.pin_level = comment.pin_level
        data_record.content = comment.content
        data_record.parent_comment_id = comment.parent_comment_id
        
        # 保存额外字段到 extra
        data_record.extra_data.user = comment.user
        data_record.extra_data.files = comment.files
        data_record.extra_data.ref_comment_id = comment.ref_comment_id
        data_record.extra_data.ref_user_id = comment.ref_user_id
        data_record.extra = jsonutil.to_json(data_record.extra_data.to_dict())
        
        comment_service.create_data(data_record)
        xmanager.fire("comment.create", comment)
        return index_id
        
    @classmethod
    def update(cls, comment: CommentVO, update_ctime = False):
        assert comment != None
        assert comment.user != None
        assert comment.note_id != None
        
        old_version = comment.version
        
        comment.update_time = dateutil.timestamp_ms()
        if comment.create_time == 0:
            comment.create_time = comment.update_time

        # 更新 comment_data 表
        data_record = comment_service.get_data_by_id(comment.id)
        if data_record is None:
            raise ValueError(f"comment data not found: id={comment.id}")
        
        # 构建新记录
        new_record = CommentDataRecord()
        new_record.id = comment.id
        new_record.create_time = comment.create_time
        new_record.update_time = comment.update_time
        new_record.version = comment.version + 1  # 使用调用方传入的 version 递增
        new_record.type = comment.type
        new_record.user_id = comment.user_id
        new_record.target_id = int(comment.note_id)
        new_record.pin_level = comment.pin_level
        new_record.content = comment.content
        new_record.parent_comment_id = comment.parent_comment_id
        
        # 保存额外字段到 extra
        new_record.extra_data.user = comment.user
        new_record.extra_data.files = comment.files
        new_record.extra_data.ref_comment_id = comment.ref_comment_id
        new_record.extra_data.ref_user_id = comment.ref_user_id
        new_record.extra = jsonutil.to_json(new_record.extra_data.to_dict())
        
        rows = comment_service.update_data(new_record, old_version=old_version)
        if rows == 0:
            raise ValueError(f"更新冲突，请刷新页面后重试")
        
        if update_ctime:
            # 更新 comment_index 表的 ctime
            comment_service.update_ctime(id = int(comment.id), ctime=dateutil.format_datetime(comment.create_time, is_ms=True))

        xmanager.fire("comment.update", comment)
        
    @classmethod
    def delete_by_id(cls, comment_id=0):
        comment = get_comment(comment_id)
        if comment != None:
            comment_service.delete_data_by_id(int(comment_id))
            xmanager.fire("comment.delete", comment)
        comment_service.delete_by_id(int(comment_id))

    @classmethod
    def get_index_by_id(cls, comment_id=0, user_id=0):
        return comment_service.get_by_id(comment_id=comment_id, user_id=user_id)
    
    @classmethod
    def update_index(cls, index: CommentIndexRecord):
        return comment_service.update(index)

def list_comments_by_idx_list(idx_list: typing.List[CommentIndexRecord], user_name=""):
    """通过索引查询评论
    :param {list} idx_list: 索引对象列表
    :param {str} user_name: 用于处理删除数据的user_name, 可以不传
    """
    result = []
    for index in idx_list:
        data_record = comment_service.get_data_by_id(index.id)
        if data_record != None:
            item = CommentVO()
            item.id = index.id
            item.type = data_record.type
            item.user_id = data_record.user_id
            item.note_id = data_record.target_id
            item.pin_level = data_record.pin_level
            item.content = data_record.content
            item.create_time = data_record.create_time
            item.update_time = data_record.update_time
            
            # 从 extra_data 恢复字段
            extra_data = data_record.extra_data
            item.user = extra_data.user
            item.files = extra_data.files
            item.ref_comment_id = extra_data.ref_comment_id
            item.ref_user_id = extra_data.ref_user_id
            item.parent_comment_id = data_record.parent_comment_id
            
            result.append(item)
        else:
            item = CommentVO()
            item.content = "[数据被删除]"
            item.update_index(index)
            result.append(item)
    return result

def _get_order(order=""):
    if order == "oldest":
        return "pin_level desc, ctime asc"
    return "pin_level desc, ctime desc"

def _get_order_by_user(order=""):
    if order == "oldest":
        return "ctime asc"
    
    return "ctime desc"

def list_comments(note_id=0, offset=0, limit=100, user_name="", order="latest"):
    assert note_id > 0
    index_list = comment_service.list(target_id=note_id, offset=offset,limit=limit, order = _get_order(order))
    return list_comments_by_idx_list(index_list, user_name=user_name)

def list_comments_by_user(user_id=0, date="", offset=0, limit=0, order=""):
    idx_list = comment_service.list(user_id=user_id,date=date,offset=offset,limit=limit, order=_get_order_by_user(order))
    comments = list_comments_by_idx_list(idx_list)
    # 为一级评论计算回复数量
    for comment in comments:
        if comment.parent_comment_id == 0:
            comment.reply_count = count_replies(comment.note_id, comment.id)
    return comments


def count_comments_by_user(user_id: int=0, date: str=""):
    return comment_service.count(user_id=user_id, date=date)

def list_replies(note_id: int=0, parent_comment_id: int=0, offset: int=0, limit: int=100):
    """获取某个评论的回复列表"""
    assert parent_comment_id > 0
    
    # 获取总数
    total = comment_service.count(target_id=note_id, parent_comment_id=parent_comment_id)
    
    # 直接使用数据库分页
    idx_list = comment_service.list(target_id=note_id, parent_comment_id=parent_comment_id, offset=offset, limit=limit, order="ctime asc")
    replies = list_comments_by_idx_list(idx_list)
    
    return replies, total

def count_replies(note_id: int=0, parent_comment_id: int=0):
    """获取某个评论的回复数量"""
    return comment_service.count(target_id=note_id, parent_comment_id=parent_comment_id)

def list_parent_comments(note_id: int=0, offset: int=0, limit: int=100, user_name: str="", order: str="latest"):
    """获取一级评论（不含回复）"""
    # 获取总数
    total = comment_service.count(target_id=note_id, parent_comment_id=0)
    
    # 直接使用数据库分页
    idx_list = comment_service.list(target_id=note_id, parent_comment_id=0, offset=offset, limit=limit, order=_get_order(order))
    
    # 使用 list_comments_by_idx_list 处理评论
    comments = list_comments_by_idx_list(idx_list, user_name=user_name)
    
    # 计算回复数量
    for comment in comments:
        if comment.parent_comment_id == 0:
            comment.reply_count = count_replies(note_id, comment.id)
    
    return comments, total

def get_comment(comment_id: int=0):
    """通过comment_id实际上是根据key获取comment"""
    index = comment_service.get_by_id(comment_id)
    if index is None:
        return None
    
    data_record = comment_service.get_data_by_id(comment_id)
    if data_record is None:
        return None
    
    item = CommentVO()
    item.id = index.id
    item.type = data_record.type
    item.user_id = data_record.user_id
    item.note_id = data_record.target_id
    item.pin_level = data_record.pin_level
    item.content = data_record.content
    item.create_time = data_record.create_time
    item.update_time = data_record.update_time
    item.version = data_record.version
    
    # 从 extra_data 恢复字段
    extra_data = data_record.extra_data
    item.user = extra_data.user
    item.files = extra_data.files
    item.ref_comment_id = extra_data.ref_comment_id
    item.ref_user_id = extra_data.ref_user_id
    item.parent_comment_id = data_record.parent_comment_id
    
    return item

def create_comment(comment: CommentVO):
    return CommentDao.create(comment)

def delete_comment(comment_id):
    return CommentDao.delete_by_id(comment_id)

def delete_index(comment_id):
    comment_service.delete_by_id(int(comment_id))

def count_comment(user_name):
    user_id = xauth.UserDao.get_id_by_name(user_name)
    return comment_service.count(user_id=user_id)


def count_comment_by_note(note_id):
    try:
        return comment_service.count(target_id=int(note_id))
    except:
        return 0

def search_comment(user_name, *, keywords=[], offset=0, 
                   limit=xconfig.PAGE_SIZE, note_id=None) -> typing.List[CommentVO]:
    if user_name is None:
        return []
    user_id = xauth.UserDao.get_id_by_name(user_name)
    target_id=0
    if note_id != None:
        target_id=int(note_id)
    
    page_builder = PageBuilder(offset=offset, limit=limit)
    
    # 使用迭代器分批获取数据，避免内存压力
    for idx_list in comment_service.list_iter(user_id=user_id, target_id=target_id, batch_size=100):
        # 分批查询详情并过滤
        comments = list_comments_by_idx_list(idx_list)
        for comment in comments:
            if not keywords:
                page_builder.add_record(comment)
            else:
                content = comment.content.lower()
                if textutil.contains_all(content, keywords):
                    page_builder.add_record(comment)
            
        if page_builder.reached_limit:
            break

    return page_builder.records


def drop_comment_table():
    pass


def fix_comment(comment):
    pass

