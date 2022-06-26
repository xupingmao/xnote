# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/04 22:07:44
# @modified 2022/04/16 21:57:34
# @filename dao_comment.py


import xutils
import xconfig

from xutils import dbutil
from xutils import textutil


def register_note_table(name, description, user_attr=None):
    dbutil.register_table(name, description, "note", user_attr=user_attr)


register_note_table("comment", "评论模型")
dbutil.register_table_index("comment", "user", "用户索引", index_type="copy")
dbutil.register_table_index("comment", "note_id", "笔记ID索引", index_type="copy")

NOTE_DAO = xutils.DAO("note")

_comment_db = dbutil.get_table("comment")


def list_comments(note_id, offset=0, limit=100):
    db = _comment_db
    comments = db.list_by_index(
        "note_id", index_value=note_id, reverse=True, offset=offset, limit=limit)
    for item in comments:
        item.id = item._key
    return comments


def handle_comments_by_user(handle_func, user_name, date=None, offset=0, limit=100):
    list_func = None

    if date is not None and date != "":
        def list_func(key, value):
            if value.ctime is None:
                return False
            return value.ctime.startswith(date)

    if handle_func == dbutil.prefix_count:
        return _comment_db.count_by_index("user", index_value=user_name, filter_func=list_func)

    return _comment_db.list_by_index("user", index_value=user_name, filter_func=list_func,
                                     offset=offset, limit=limit, reverse=True)


def list_comments_by_user(*args, **kw):
    result = []
    for value in handle_comments_by_user(dbutil.prefix_list, *args, **kw):
        value["id"] = value._id
        result.append(value)
    return result


def count_comments_by_user(*args, **kw):
    return handle_comments_by_user(dbutil.prefix_count, *args, **kw)


def get_comment(comment_id):
    value = _comment_db.get_by_key(comment_id)
    if value != None:
        value.id = comment_id
    return value


def check_comment(comment):
    assert comment != None, "comment is None"
    assert comment.user != None, "comment.user is None"
    assert comment.type in (None, "list_item"), "comment.type is invalid"


def create_comment(comment):
    check_comment(comment)

    _comment_db.insert(comment)

    NOTE_DAO.refresh_note_stat_async(comment["user"])


def update_comment(comment):
    assert comment != None
    assert comment.user != None
    assert comment.note_id != None

    _comment_db.update(comment)


def delete_comment(comment_id):
    comment = get_comment(comment_id)
    if comment != None:
        _comment_db.delete(comment)
        NOTE_DAO.refresh_note_stat_async(comment.user)


def count_comment(user_name):
    return _comment_db.count_by_index("user", index_value=user_name)


def count_comment_by_note(note_id):
    return _comment_db.count_by_index("note_id", index_value=note_id)


def search_comment(user_name, *, keywords, offset=0, limit=xconfig.PAGE_SIZE, note_id=None):
    assert user_name != None, "user_name can not be None"

    def search_comment_filter(key, value):
        content = value.content.lower()
        if textutil.contains_all(content, keywords):
            return True
        else:
            return False

    if note_id != None and note_id != "":
        # 按笔记维度搜索
        result = _comment_db.list_by_index("note_id", index_value=note_id,
                                           filter_func=search_comment_filter, offset=offset, limit=limit)
    else:
        # 按用户维度搜索
        result = _comment_db.list_by_index("user", index_value=user_name,
                                           filter_func=search_comment_filter, offset=offset, limit=limit)

    for item in result:
        item.id = item._key
    return result


def drop_comment_table():
    _comment_db.drop_index("user")
    _comment_db.drop_index("note_id")
    
    for item in _comment_db.iter(-1):
        _comment_db.delete(item)


def fix_comment(comment):
    _comment_db.insert(comment)


# comments
xutils.register_func("note.save_comment", create_comment)
xutils.register_func("note.delete_comment", delete_comment)
xutils.register_func("note.update_comment", update_comment)
xutils.register_func("note.search_comment", search_comment)
xutils.register_func("note.get_comment",  get_comment)

xutils.register_func("note.list_comments", list_comments)
xutils.register_func("note.list_comments_by_user", list_comments_by_user)
xutils.register_func("note.count_comment", count_comment)
xutils.register_func("note.count_comment_by_user", count_comments_by_user)
xutils.register_func("note.count_comment_by_note", count_comment_by_note)
