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
from xutils import dbutil
from xutils import textutil
from xutils import dateutil
from xutils.db.dbutil_helper import PageBuilder, batch_iter
from xnote.service import CommentService, Comment, CommentIndexDO
from xutils.base import BaseDataRecord

NOTE_DAO = xutils.DAO("note")

_comment_db = dbutil.get_table("comment")

comment_service = CommentService()

class CommentDO(BaseDataRecord):
    def __init__(self, **kw):
        now = dateutil.format_datetime()
        self.id = 0
        self.user = ""
        self.user_id = 0
        self.note_id = 0
        self.type = ""
        self.content = ""
        self.ctime = now
        self.mtime = now
        self.update(kw)


class CommentDao:

    valid_type_set = set(["", None, "list_item"])
    
    @classmethod
    def check(cls, comment: CommentDO):
        assert comment != None, "comment is None"
        assert comment.user != None, "comment.user is None"
        assert comment.type in cls.valid_type_set, "comment.type is invalid"
        assert comment.note_id != None
        assert comment.content != None
        assert comment.content != ""
    
    @classmethod
    def create(cls, comment: CommentDO):
        assert isinstance(comment, CommentDO)
        cls.check(comment)
        comment.ctime = dateutil.format_datetime()
        index_id = comment_service.create(type=comment.type, user_id=comment.user_id, target_id=int(comment.note_id))
        _comment_db.update_by_id(str(index_id), comment)
        xmanager.fire("comment.create", comment)
        return index_id
        
    @classmethod
    def update(cls, comment: CommentDO):
        assert comment != None
        assert comment.user != None
        assert comment.note_id != None
        comment.mtime = dateutil.format_datetime()

        _comment_db.update(comment)
        xmanager.fire("comment.update", comment)
        
    @classmethod
    def delete_by_id(cls, comment_id=0):
        comment = get_comment(comment_id)
        if comment != None:
            _comment_db.delete(comment)
            xmanager.fire("comment.delete", comment)
        comment_service.delete_by_id(int(comment_id))


def list_comments_by_idx_list(idx_list: typing.List[CommentIndexDO], user_name=""):
    """通过索引查询评论
    :param {list} idx_list: 索引对象列表
    :param {str} user_name: 用于处理删除数据的user_name, 可以不传
    """
    id_list = [str(item.id) for item in idx_list]
    comment_dict = _comment_db.batch_get_by_id(id_list)
    result = [] # type: list[CommentDO]
    for index in idx_list:
        id_str = str(index.id)
        item = comment_dict.get(id_str)
        if item != None:
            item_do = CommentDO.from_dict(item)
            item_do.id = index.id
            result.append(item_do)
        else:
            item = CommentDO()
            item.id = index.id
            item.user = user_name
            item.user_id = index.user_id
            item.content = "[数据被删除]"
            result.append(item)
    return result

def list_comments(note_id, offset=0, limit=100, user_name=""):
    index_list = comment_service.list(target_id=int(note_id), offset=offset,limit=limit)
    return list_comments_by_idx_list(index_list, user_name=user_name)

def list_comments_by_user(user_id=0, date="", offset=0, limit=0):
    idx_list = comment_service.list(user_id=user_id,date=date,offset=offset,limit=limit,order="ctime desc")
    return list_comments_by_idx_list(idx_list)


def count_comments_by_user(user_id=0, date=""):
    return comment_service.count(user_id=user_id, date=date)

def get_comment(comment_id = 0):
    """通过comment_id实际上是根据key获取comment"""
    value = _comment_db.get_by_id(str(comment_id))
    if value != None:
        value["id"] = comment_id
        return CommentDO(**value)
    return None

def create_comment(comment: CommentDO):
    return CommentDao.create(comment)

def update_comment(comment):
    return CommentDao.update(comment)

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

def search_comment(user_name, *, keywords=[], offset=0, limit=xconfig.PAGE_SIZE, note_id=None):
    if user_name is None:
        return []
    user_id = xauth.UserDao.get_id_by_name(user_name)
    target_id=0
    if note_id != None:
        target_id=int(note_id)
    
    idx_list = comment_service.list(what="id", user_id=user_id, target_id=target_id, limit=10000)
    page_builder = PageBuilder(offset=offset,limit=limit)
    for sub_idx_list in batch_iter(idx_list, batch_size=20):
        comments = list_comments_by_idx_list(sub_idx_list)
        for comment in comments:
            content = comment.content.lower()
            if textutil.contains_all(content, keywords):
                page_builder.add_record(comment)
                if len(page_builder.records) >= limit:
                    break

    return page_builder.records


def drop_comment_table():
    _comment_db.drop_index("user")
    _comment_db.drop_index("note_id")
    
    for item in _comment_db.iter(-1):
        _comment_db.delete(item)


def fix_comment(comment):
    _comment_db.insert(comment)

