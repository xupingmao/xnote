# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/12/29 23:48:27
# @modified 2021/12/30 22:57:29
# @filename dao_log.py

"""笔记相关的访问日志有两个部分：
1. 某个用户对某个笔记的访问记录，用于统计个人对笔记的行为倾向，
    记录在 user_note_log.visit_cnt 中

2. 所有用户对某个笔记的访问记录，用于统计群体对笔记的行为倾向，
    记录在 note_index.visit_cnt 中
"""

import xauth
import xutils
import xmanager
import xconfig
from xutils import dbutil
from xutils import dateutil
from xutils import Storage

dbutil.register_table("user_note_log", "用户笔记操作日志")
dbutil.register_table("note_migrate_log", "笔记迁移日志")

dbutil.register_table_index("user_note_log", "visit_cnt")
dbutil.register_table_index("user_note_log", "atime")
dbutil.register_table_index("user_note_log", "mtime")
dbutil.register_table_index("user_note_log", "ctime")


NOTE_DAO = xutils.DAO("note")
MAX_EDIT_LOG    = 500
MAX_VIEW_LOG    = 500

def log_debug(fmt, *args):
    print(dateutil.format_time(), fmt.format(*args))

def is_debug_enabled():
    return xconfig.DEBUG

def get_user_note_log_table(user_name):
    assert user_name != None, "invalid user_name:%r" % user_name
    return dbutil.get_table("user_note_log", user_name = user_name)

def get_note_migrate_log_table():
    return dbutil.get_hash_table("note_migrate_log")

def is_migrate_done(op_flag):
    db = get_note_migrate_log_table()
    return db.get(op_flag) == "1"

def mark_migrate_done(op_flag):
    db = get_note_migrate_log_table()
    db.put(op_flag, "1")

@xutils.timeit_deco(name = "_update_log", switch_func = is_debug_enabled)
def _update_log(user_name, note, increment = 1, insert_only = False):
    # 部分历史数据是int类型，所以需要转换一下
    note_id = str(note.id)

    db = get_user_note_log_table(user_name)

    log = db.get_by_id(note_id)
    
    if log is None:
        log = Storage()
        log.note_id = note_id
        log.visit_cnt  = increment
        log.atime = note.atime
        log.mtime = note.mtime
        log.ctime = note.ctime
        db.insert(log, id_type = None, id_value = note_id)
    else:
        if insert_only:
            log_debug("skip for insert_only mode, note_id:{!r}", note_id)
            return
        if log.visit_cnt is None:
            log.visit_cnt = 1
        log.visit_cnt += increment
        log.atime = note.atime
        log.mtime = note.mtime
        log.ctime = note.ctime
        db.update(log)

def get_note_ids_from_logs(logs):
    return list(map(lambda x:x.note_id, logs))

@xutils.timeit(name = "NoteDao.ListRecentViewed", logfile = True, logargs = True)
def list_recent_viewed(creator = None, offset = 0, limit = 10):
    if limit is None:
        limit = xconfig.PAGE_SIZE

    user = xauth.current_name()
    if user is None:
        user = "public"

    db = get_user_note_log_table(user)
    logs = db.list_by_index("atime", offset = offset, limit = limit, reverse = True)

    note_ids = get_note_ids_from_logs(logs)

    return NOTE_DAO.batch_query_list(note_ids)

def list_hot(user_name, offset = 0, limit = 100):
    if limit < 0:
        limit = MAX_VIEW_LOG

    db = get_user_note_log_table(user_name)
    logs = db.list_by_index("visit_cnt", 
        offset = offset, limit = limit, reverse = True)

    hot_dict = dict()
    for log in logs:
        hot_dict[log.note_id] = log.visit_cnt
        
    note_ids = get_note_ids_from_logs(logs)

    notes = NOTE_DAO.batch_query_list(note_ids)
    for note in notes:
        note.hot_index = hot_dict.get(note.id)
    return notes

def list_most_visited(user_name, offset, limit):
    return list_hot(user_name, offset, limit)

@xutils.timeit(name = "NoteDao.ListRecentEdit:leveldb", logfile = True, logargs = True)
def list_recent_edit(user_name = None, offset = 0, limit = None, skip_deleted = True):
    """通过KV存储实现"""
    if limit is None:
        limit = xconfig.PAGE_SIZE
    
    user = xauth.current_name()
    if user is None:
        user = "public"

    db = get_user_note_log_table(user_name)
    logs = db.list_by_index("mtime", offset = offset, limit = limit, reverse = True)
    note_ids = get_note_ids_from_logs(logs)
    return NOTE_DAO.batch_query_list(note_ids)

@xutils.timeit(name = "NoteDao.ListRecentCreated", logfile = True)
def list_recent_created(user_name = None, offset = 0, limit = 10, skip_archived = False):
    if limit is None:
        limit = xconfig.PAGE_SIZE

    user = xauth.current_name()
    if user is None:
        user = "public"

    db = get_user_note_log_table(user_name)
    logs = db.list_by_index("ctime", offset = offset, limit = limit, reverse = True)
    note_ids = get_note_ids_from_logs(logs)
    return NOTE_DAO.batch_query_list(note_ids)

def count_visit_log(user_name):
    return get_user_note_log_table(user_name).count()

def delete_visit_log(user_name, note_id):
    db = get_user_note_log_table(user_name)
    db.delete_by_id(note_id)

def add_visit_log(user_name, note):
    return _update_log(user_name, note)

def add_edit_log(user_name, note):
    return _update_log(user_name, note)

def add_create_log(user_name, note):
    return _update_log(user_name, note)

#### 重建访问日志
def rebuild_visit_log():
    if is_migrate_done("note_visit_log"):
        print("note_visit_log migrate done")
        return

    db = dbutil.get_table("note_index")
    for note in db.iter(limit = -1):
        note_id = str(note.id)
        if note.creator is None:
            print("invalid note:%r", note.id)
            continue
        if note.is_deleted:
            delete_visit_log(note.creator, note_id)
            continue
        increment = note.visited_cnt or 1
        _update_log(note.creator, note, increment)

    mark_migrate_done("note_visit_log")


@xmanager.listen("sys.reload")
def check_and_rebuild_note_log(ctx):
    rebuild_visit_log()

# 读操作
xutils.register_func("note.count_visit_log", count_visit_log)
xutils.register_func("note.list_recent_viewed", list_recent_viewed)
xutils.register_func("note.list_hot", list_hot)
xutils.register_func("note.list_recent_edit", list_recent_edit)
xutils.register_func("note.list_recent_created", list_recent_created)
xutils.register_func("note.list_most_visited", list_most_visited)

# 写操作
xutils.register_func("note.add_edit_log", add_edit_log)
xutils.register_func("note.add_visit_log", add_visit_log)
xutils.register_func("note.add_create_log", add_create_log)
xutils.register_func("note.delete_visit_log", delete_visit_log)
