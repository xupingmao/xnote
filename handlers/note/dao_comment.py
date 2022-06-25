# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/04 22:07:44
# @modified 2022/04/16 21:57:34
# @filename dao_comment.py


import xutils
import xconfig

from xutils import dbutil
from xutils import dateutil
from xutils import textutil

def register_note_table(name, description):
    dbutil.register_table(name, description, "note")

register_note_table("note_comment", "笔记的评论")
register_note_table("comment_index", "用户维度的评论索引")
NOTE_DAO = xutils.DAO("note")

_comment_db = dbutil.get_table("note_comment")

def get_comment_table(note_id = None):
    return dbutil.get_table("note_comment", user_name = note_id)

def get_index_table(user_name):
    return dbutil.get_table("comment_index", user_name = user_name)

def list_comments(note_id, offset = 0, limit = 100):
    db = get_comment_table(note_id)
    comments = db.list(reverse = True, offset = offset, limit = limit)
    for item in comments:
        item.id = item._key
    return comments

def handle_comments_by_user(handle_func, user_name, date = None, offset = 0, limit = 100):
    list_func = None

    if date is not None and date != "":
        def list_func(key, value):
            if value.ctime is None:
                return False
            return value.ctime.startswith(date)

    return handle_func("comment_index:%s" % user_name, list_func, 
        offset = offset, limit = limit, reverse = True, include_key = True)

def list_comments_by_user(*args, **kw):
    result = []
    for key, value in handle_comments_by_user(dbutil.prefix_list, *args, **kw):
        value["id"] = key
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

    timeseq = dbutil.timeseq()

    comment["timeseq"] = timeseq
    comment["ctime"]   = dateutil.format_time()
    
    _comment_db.update_by_id(timeseq, comment, user_name = comment["note_id"])

    index_key = "comment_index:%s:%s" % (comment["user"], timeseq)
    comment_index = comment.copy()
    dbutil.put(index_key, comment_index)

    NOTE_DAO.refresh_note_stat_async(comment["user"])

def update_comment(comment):
    assert comment != None
    assert comment.timeseq != None
    assert comment.user != None

    timeseq = comment.timeseq

    db = get_comment_table()
    db.update_by_key(comment.id, comment)

    index_db = get_index_table(comment.user)
    index_db.update_by_id(timeseq, comment)


def delete_comment(comment_id):
    comment = get_comment(comment_id)
    if comment != None:
        dbutil.delete(comment_id)
        index_db = get_index_table(comment.user)
        if comment.timeseq != None:
            index_db.delete_by_id(comment.timeseq)
        NOTE_DAO.refresh_note_stat_async(comment.user)

def count_comment(user_name):
    return dbutil.count_table("comment_index:%s" % user_name)

def count_comment_by_note(note_id):
    db = get_comment_table(note_id)
    return db.count()

def search_comment(user_name, keywords, offset = 0, limit = None):
    assert user_name != None, "user_name can not be None"

    if limit is None:
        limit = xconfig.PAGE_SIZE

    def search_comment_filter(key, value):
        content = value.content.lower()
        if textutil.contains_all(content, keywords):
            return True
        else:
            return False

    db = get_index_table(user_name)
    return db.list(filter_func = search_comment_filter, offset = offset, limit = limit)

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

