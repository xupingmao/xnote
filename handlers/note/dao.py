# encoding=utf-8
# Created by xupingmao on 2017/04/16
# @modified 2020/11/22 15:56:04

"""资料的DAO操作集合
DAO层只做最基础的数据库交互，不做权限校验（空校验要做），业务状态检查之类的工作

一些表的说明
note_full:<note_id>              = 笔记的内容，包含一些属性（部分属性比如访问时间、访问次数不是实时更新的）
note_index:<note_id>             = 笔记索引
note_tiny:<user>:<note_id>       = 用户维度的笔记索引
notebook:<user>:<note_id>        = 用户维度的笔记本(项目)索引
token:<uuid>                     = 用于链接分享的令牌
note_history:<note_id>:<version> = 笔记的历史版本
note_comment:<note_id>:<timeseq> = 笔记的评论
comment_index:<user>:<timeseq>   = 用户维度的评论索引
search_history:<user>:<timeseq>  = 用户维度的搜索历史

TODO:
note_public:<note_id>            = 公开的笔记索引
"""
import time
import math
import re
import six
import web.db as db
import os
import xconfig
import xtables
import xutils
import xauth
import xmanager
import copy
import threading
from collections import Counter
from xutils import readfile, savetofile, sqlite3, Storage
from xutils import dateutil, cacheutil, Timer, dbutil, textutil, fsutil
from xutils import attrget

dbutil.register_table("note_full", "笔记完整信息 <note_full:note_id>")
dbutil.register_table("note_index", "笔记索引，不包含内容 <note_index:note_id>")
dbutil.register_table("note_tiny", "用户维度的笔记索引 <note_tiny:user:note_id>")
dbutil.register_table("notebook", "笔记分组")
dbutil.register_table("token", "用于分享的令牌")
dbutil.register_table("note_history", "笔记的历史版本")
dbutil.register_table("note_comment", "笔记的评论")
dbutil.register_table("comment_index", "用户维度的评论索引")
dbutil.register_table("search_history", "搜索历史")
dbutil.register_table("note_edit_log", "笔记编辑日志")
dbutil.register_table("note_visit_log", "笔记访问日志")
dbutil.register_table("note_public", "公共笔记索引")
dbutil.register_table("note_tags", "笔记标签 <note_tags:user:note_id>")

DB_PATH         = xconfig.DB_PATH
MAX_EDIT_LOG    = 500
MAX_VIEW_LOG    = 500

NOTE_ICON_DICT = {
    "group"   : "fa-folder orange",
    "csv"     : "fa-table",
    "table"   : "fa-table",
    "post"    : "fa-file-word-o",
    "html"    : "fa-file-word-o",
    "gallery" : "fa-photo",
    "list"    : "fa-list",
    "plan"    : "fa-calendar-check-o",
}

CREATE_LOCK = threading.RLock()

class NoteSchema:
    """这个类主要是说明结构"""

    # 基本信息
    id          = "主键ID"
    name        = "笔记名称"
    ctime       = "创建时间"
    mtime       = "修改时间"
    atime       = "访问时间"
    type        = "类型"
    category    = "所属分类"  # 一级图书分类
    size        = "大小"
    parent_id   = "父级节点ID"
    content     = "纯文本内容"
    data        = "富文本内容"
    is_deleted  = "是否删除"
    archived    = "是否归档"

    # 权限控制
    creator     = "创建者"
    is_public   = "是否公开"
    token       = "分享token"
    
    # 统计信息
    priority    = "优先级"
    visited_cnt = "访问次数"
    orderby     = "排序方式"
    hot_index   = "热门指数"

def format_note_id(id):
    return "%020d" % int(id)

def get_root():
    root = Storage()
    root.name = "根目录"
    root.type = "group"
    root.size = None
    root.id   = 0
    root.parent_id = 0
    root.content = ""
    root.priority = 0
    build_note_info(root)
    return root

def get_default_group():
    group = Storage()
    group.name = "默认分组"
    group.type = "group"
    group.size = None
    group.id   = "default"
    group.parent_id = 0
    group.content = ""
    group.priority = 0
    build_note_info(group)
    group.url = "/note/default"
    return group

def get_archived_group():
    group = Storage()
    group.name = "归档分组"
    group.type = "group"
    group.size = None
    group.id   = "archived"
    group.parent_id = 0
    group.content = ""
    group.priority = 0
    build_note_info(group)
    group.url = "/note/archived"
    return group



def batch_query(id_list):
    creator = xauth.current_name()
    result = dict()
    for id in id_list:
        note = dbutil.get("note_index:%s" % id)
        if note:
            result[id] = note
            build_note_info(note)
    return result

def sort_by_name(notes):
    notes.sort(key = lambda x: x.name)

def sort_by_name_desc(notes):
    notes.sort(key = lambda x: x.name, reverse = True)

def sort_by_mtime_desc(notes):
    notes.sort(key = lambda x: x.mtime, reverse = True)

def sort_by_ctime_desc(notes):
    notes.sort(key = lambda x: x.ctime, reverse = True)

SORT_FUNC_DICT = {
    "name": sort_by_name,
    "name_desc": sort_by_name_desc,
    "mtime_desc": sort_by_mtime_desc,
    "ctime_desc": sort_by_ctime_desc,
}

def sort_notes(notes, orderby = "name"):
    sort_func = SORT_FUNC_DICT.get(orderby, sort_by_mtime_desc)
    sort_func(notes)

    # 置顶笔记
    notes.sort(key = lambda x: x.priority, reverse = True)
    # 文件夹放在前面
    notes.sort(key = lambda x: 0 if x.type == "group" else 1)
    fix_notes_info(notes)


def fix_notes_info(notes):
    for note in notes:
        build_note_info(note)

def build_note_info(note):
    if note:
        # note.url = "/note/view?id={}".format(note["id"])
        note.url = "/note/{}".format(note["id"])
        if note.priority is None:
            note.priority = 0

        if note.content is None:
            note.content = ''

        if note.data is None:
            note.data = ''
        # process icon
        note.icon = NOTE_ICON_DICT.get(note.type, "fa-file-text-o")
        note.id   = str(note.id)

        if note.type in ("list", "csv"):
            note.show_edit = False

        if note.visited_cnt is None:
            note.visited_cnt = 0

        if note.orderby is None:
            note.orderby = "name"

        if note.category is None:
            note.category = "000"
            
    return note

def convert_to_path_item(note):
    return Storage(name = note.name, url = note.url, id = note.id, 
        type = note.type, priority = note.priority, is_public = note.is_public)

@xutils.timeit(name = "NoteDao.ListPath:leveldb", logfile = True)
def list_path(file, limit = 5):
    pathlist = []
    while file is not None:
        pathlist.insert(0, convert_to_path_item(file))
        file.url = "/note/%s" % file.id
        if len(pathlist) >= limit:
            break
        if str(file.id) == "0":
            break

        # 处理根目录
        if str(file.parent_id) == "0":
            if file.type != "group":
                pathlist.insert(0, get_default_group())
            elif file.archived:
                pathlist.insert(0, get_archived_group())
            pathlist.insert(0, convert_to_path_item(get_root()))
            break
        
        file = get_by_id(file.parent_id, include_full = False)
    return pathlist

@xutils.timeit(name = "NoteDao.GetById:leveldb", logfile = True)
def get_by_id(id, include_full = True):
    if id == "" or id is None:
        return None
    if id == 0 or id == "0":
        return get_root()

    note_index = dbutil.get("note_index:%s" % id)

    if not include_full and note_index != None:
        build_note_info(note_index)
        return note_index

    note = dbutil.get("note_full:%s" % id)
    if note and not include_full:
        del note.content
        del note.data
    if note_index:
        note.name = note_index.name
        note.mtime = note_index.mtime
        note.atime = note_index.atime
        note.size  = note_index.size
        note.tags  = note_index.tags
        note.parent_id = note_index.parent_id
        note.visited_cnt = note_index.visited_cnt
        note.hot_index = note_index.hot_index
    if note:
        build_note_info(note)
    return note

def get_by_id_creator(id, creator, db=None):
    note = get_by_id(id)
    if note and note.creator == creator:
        return note
    return None

def get_by_token(token):
    token_info = dbutil.get("token:%s" % token)
    if token_info != None and token_info.type == "note":
        return get_by_id(token_info.id)
    return None

def create_note_base(note_dict, date_str):
    if date_str is None or date_str == "":
        note_id = dbutil.timeseq()
        note_dict["id"] = note_id
        put_note_to_db(note_id, note_dict)
        return note_id
    else:
        timestamp = int(dateutil.parse_date_to_timestamp(date_str) * 1000)
        try:
            CREATE_LOCK.acquire()

            while True:
                note_id = format_note_id(timestamp)
                note_dict["ctime"] = dateutil.format_datetime(timestamp/1000)
                old = get_by_id(note_id)
                if old is None:
                    note_dict["id"] = note_id
                    put_note_to_db(note_id, note_dict)
                    return note_id
                else:
                    timestamp += 1
        finally:
            CREATE_LOCK.release()

def create_note(note_dict, date_str = None):
    content   = note_dict["content"]
    data      = note_dict["data"]
    creator   = note_dict["creator"]
    priority  = note_dict["priority"]
    mtime     = note_dict["mtime"]
    parent_id = note_dict.get("parent_id", "0")
    name      = note_dict.get("name")

    # 创建笔记的基础信息
    note_id = create_note_base(note_dict, date_str)
    
    # 更新分组下面页面的数量
    update_children_count(note_dict["parent_id"])

    xmanager.fire("note.add", dict(name=name, type=type, id = note_id))

    # 创建对应的文件夹
    if type == "gallery":
        dirname = os.path.join(xconfig.UPLOAD_DIR, creator, str(note_id))
        xutils.makedirs(dirname)

    # 更新统计数量
    refresh_note_stat(creator)
    # 更新目录修改时间
    touch_note(parent_id)

    return note_id

def create_token(type, id):
    uuid = textutil.generate_uuid()
    token_info = Storage(type = type, id = id)
    dbutil.put("token:%s" % uuid, token_info)
    return uuid

def get_id_from_log(log):
    if isinstance(log, dict):
        return log.get("id")
    else:
        # 老数据，都是id
        return log

def log_list_to_id_list(log_list):
    result = []
    for log in log_list:
        result.append(get_id_from_log(log))
    return result

def delete_old_edit_log(creator, note_id):
    counter = Counter()
    def filter_func(key, value):
        log_id = get_id_from_log(value)
        counter.update("e")
        return log_id == note_id or counter["e"] > MAX_EDIT_LOG
    old_logs = dbutil.prefix_list("note_edit_log:%s:" % creator, filter_func, include_key = True, reverse = True)
    for key, value in old_logs:
        dbutil.delete(key)

def add_edit_log(note):
    creator = note.creator
    note_id = note.id
    
    delete_old_edit_log(creator, note_id)

    key = "note_edit_log:%s:%s" % (creator, dbutil.timeseq())
    edit_log = Storage(id = note_id)
    dbutil.put(key, edit_log)

def delete_old_visit_log(creator, note_id):
    counter   = Counter()
    def filter_func(key, value):
        log_id = get_id_from_log(value)
        counter.update("v")
        return log_id == note_id or counter["v"] > MAX_VIEW_LOG

    old_logs = dbutil.prefix_list("note_visit_log:%s:" % creator, filter_func, include_key = True, reverse = True)
    for key, value in old_logs:
        dbutil.delete(key)

def add_visit_log(user_name, note):
    note_id = note.id

    # 先删除历史的浏览记录，只保留最新的
    delete_old_visit_log(user_name, note_id)

    key = "note_visit_log:%s:%s" % (user_name, dbutil.timeseq())

    visit_log = Storage(id = note_id)
    dbutil.put(key, visit_log)

def update_note_rank(note):
    mtime = note.mtime
    atime = note.atime
    creator = note.creator
    note_id = note.id
    
    if note.is_deleted:
        # TODO 删除索引
        return
        # dbutil.zrem("note_recent:%s" % creator, note_id)
        # dbutil.zrem("note_visit:%s" % creator, note_id)
        # dbutil.zrem("note_recent:public", note_id)
    if note.type != "group":
        # 分组不需要记录
        # TODO 增加修改时间和访问时间的索引
        return
    if note.is_public:
        # TODO 更新公共笔记的最近更新索引
        # dbutil.zadd("note_recent:public", mtime, note_id)
        return

def put_note_to_db(note_id, note):
    priority = note.priority
    mtime    = note.mtime
    creator  = note.creator
    atime    = note.atime

    # 删除不需要持久化的数据
    del_dict_key(note, "path")
    del_dict_key(note, "url")
    del_dict_key(note, "icon")
    del_dict_key(note, "show_edit")

    dbutil.put("note_full:%s" % note_id, note)

    # 更新索引
    update_index(note)

    # 增加编辑日志
    add_edit_log(note)

def touch_note(note_id):
    note = get_by_id(note_id)
    if note != None:
        note.mtime = dateutil.format_datetime()
        update_index(note)

def del_dict_key(dict, key):
    if key in dict:
        del dict[key]

def convert_to_index(note):
    note_index = Storage(**note)

    del_dict_key(note_index, 'path')
    del_dict_key(note_index, 'url')
    del_dict_key(note_index, 'icon')
    del_dict_key(note_index, 'data')
    del_dict_key(note_index, 'content')
    del_dict_key(note_index, 'show_edit')

    note_index.parent_id = str(note_index.parent_id)
    
    return note_index

def update_index(note):
    """更新索引的时候也会更新用户维度的索引(note_tiny)"""
    id = note['id']

    note_index = convert_to_index(note)
    dbutil.put('note_index:%s' % id, note_index)

    # 更新用户索引
    dbutil.put("note_tiny:%s:%s" % (note.creator, format_note_id(id)), note_index)

    if note.type == "group":
        dbutil.put("notebook:%s:%s" % (note.creator, format_note_id(id)), note)

    if note.is_public != None:
        update_public_index(note)

def update_public_index(note):
    if note.is_public:
        note_index = convert_to_index(note)
        dbutil.put("note_public:%s" % format_note_id(note.id), note_index)
    else:
        dbutil.delete("note_public:%s" % format_note_id(note.id))

def update_note(note_id, **kw):
    # 这里只更新基本字段，移动笔记使用 move_note
    content   = kw.get('content')
    data      = kw.get('data')
    priority  = kw.get('priority')
    name      = kw.get("name")
    atime     = kw.get("atime")
    is_public = kw.get("is_public")
    tags      = kw.get("tags")
    orderby   = kw.get("orderby")
    archived  = kw.get("archived")
    size      = kw.get("size")
    token     = kw.get("token")
    visited_cnt = kw.get("visited_cnt")

    old_parent_id = None
    new_parent_id = None

    note = get_by_id(note_id)
    if note:
        if content:
            note.content = content
        if data:
            note.data = data
        if priority != None:
            note.priority = priority
        if name:
            note.name = name
        if atime:
            note.atime = atime
        if is_public != None:
            note.is_public = is_public
        if tags != None:
            note.tags = tags
        if orderby != None:
            note.orderby = orderby
        if archived != None:
            note.archived = archived
        if size != None:
            note.size = size
        if token != None:
            note.token = token
        if visited_cnt != None:
            note.visited_cnt = visited_cnt

        old_version  = note.version
        note.mtime   = xutils.format_time()
        note.version += 1
        
        # 只修改优先级
        if len(kw) == 1 and kw.get('priority') != None:
            note.version = old_version
        # 只修改名称
        if len(kw) == 1 and kw.get('name') != None:
            note.version = old_version

        put_note_to_db(note_id, note)
        return 1
    return 0

def move_note(note, new_parent_id):
    old_parent_id = note.parent_id
    note.parent_id = new_parent_id
    # 没有更新内容，只需要更新索引数据
    update_index(note)
    
    # 更新文件夹的容量
    update_children_count(old_parent_id)
    update_children_count(new_parent_id)

    # 更新新的parent更新时间
    touch_note(new_parent_id)

def update0(note):
    """更新基本信息，比如name、mtime、content、items、priority等,不处理parent_id更新"""
    current = get_by_id(note.id)
    if current is None:
        return
    # 更新各种字段
    current_time = xutils.format_datetime()
    note.version = current.version + 1
    note.mtime   = current_time
    note.atime   = current_time
    put_note_to_db(note.id, note)

def get_by_name(creator, name):
    def find_func(key, value):
        if value.is_deleted:
            return False
        return value.name == name
    result = dbutil.prefix_list("note_tiny:%s" % creator, find_func, 0, 1)
    if len(result) > 0:
        note = result[0]
        return get_by_id(note.id)
    return None

def visit_note(user_name, id):
    note = get_by_id(id)
    if note:
        note.atime = xutils.format_datetime()
        # 访问的总字数
        if note.visited_cnt is None:
            note.visited_cnt = 0
        note.visited_cnt += 1

        # 访问热度
        if note.hot_index is None:
            note.hot_index = 0
        note.hot_index += 1

        update_index(note)
        add_visit_log(user_name, note)

def delete_note(id):
    note = get_by_id(id)
    if note is None:
        return

    if note.is_deleted != 0:
        # 已经被删除了，执行物理删除
        tiny_key  = "note_tiny:%s:%s" % (note.creator, note.id)
        full_key  = "note_full:%s" % note.id
        index_key = "note_index:%s" % note.id
        dbutil.delete(tiny_key)
        dbutil.delete(full_key)
        dbutil.delete(index_key)
        delete_history(note.id)
        return

    # 标记删除
    note.mtime = xutils.format_datetime()
    note.is_deleted = 1
    put_note_to_db(id, note)

    # 更新数量
    update_children_count(note.parent_id)
    delete_tags(note.creator, id)

    # 删除笔记本
    book_key = "notebook:%s:%s" % (note.creator, format_note_id(id))
    dbutil.delete(book_key)

    # 更新数量统计
    refresh_note_stat(note.creator)

def update_children_count(parent_id, db=None):
    if parent_id is None or parent_id == "" or parent_id == 0:
        return

    note = get_by_id(parent_id)
    if note is None:
        return

    creator        = note.creator
    children_count = count_by_parent(creator, parent_id)
    note.size      = children_count

    update_index(note)


def fill_parent_name(files):
    id_list = []
    for item in files:
        build_note_info(item)
        id_list.append(item.parent_id)

    note_dict = batch_query(id_list)
    for item in files:
        parent = note_dict.get(item.parent_id)
        if parent != None:
            item.parent_name = parent.name
        else:
            item.parent_name = None

@xutils.timeit(name = "NoteDao.ListGroup:leveldb", logfile = True)
def list_group(creator = None, orderby = "mtime_desc", skip_archived = False):
    # TODO 添加索引优化
    def list_group_func(key, value):
        if skip_archived and value.archived:
            return False
        return value.type == "group" and value.is_deleted == 0

    notes = dbutil.prefix_list("notebook:%s" % creator, list_group_func)
    sort_notes(notes, orderby)
    return notes

@xutils.timeit(name = "NoteDao.ListRootGroup:leveldb", logfile = True)
def list_root_group(creator = None, orderby = "name"):
    def list_root_group_func(key, value):
        return value.creator == creator and value.type == "group" and value.parent_id == 0 and value.is_deleted == 0

    notes = dbutil.prefix_list("notebook:%s" % creator, list_root_group_func)
    sort_notes(notes, orderby)
    return notes

def list_default_notes(creator, offset = 0, limit = -1):
    return list_by_parent(creator, 0, offset, limit, skip_group = True)

def count_group(creator):
    return dbutil.count_table("notebook:%s" % creator)

def list_public(offset, limit):
    def list_func(key, value):
        if value.is_deleted:
            return False
        return value.is_public

    notes = dbutil.prefix_list("note_tiny:", list_func, offset, limit)
    sort_notes(notes)
    return notes

def count_public():
    def list_func(key, value):
        if value.is_deleted:
            return False
        return value.is_public

    return dbutil.prefix_count("note_tiny:", list_func)

@xutils.timeit(name = "NoteDao.ListNote:leveldb", logfile = True, logargs=True)
def list_by_parent(creator, parent_id, offset = 0, limit = 1000, orderby="name", skip_group = False):
    parent_id = str(parent_id)
    # TODO 添加索引优化
    def list_note_func(key, value):
        if value.is_deleted:
            return False
        if skip_group and value.type == "group":
            return False
        return (value.is_public or value.creator == creator) and str(value.parent_id) == parent_id

    notes = dbutil.prefix_list("note_tiny:", list_note_func)
    sort_notes(notes, orderby)
    return notes[offset:offset+limit]

@xutils.timeit(name = "NoteDao.ListRecentCreated", logfile = True)
def list_recent_created(creator = None, offset = 0, limit = 10, skip_archived = False):
    def list_func(key, value):
        if skip_archived and value.archived:
            return False
        return value.is_deleted != 1

    result  = dbutil.prefix_list("note_tiny:%s" % creator, list_func, offset, limit, reverse = True)
    fill_parent_name(result)
    return result

def list_note_by_log(log_prefix, creator, offset = 0, limit = -1):
    """通过日志来查询笔记列表
    @param {string} log_prefix 日志表前缀
    @param {string} creator 用户名称
    @param {int} offset 开始下标（包含）
    @param {int} limit 返回数量
    """
    log_list  = dbutil.prefix_list("%s:%s" % (log_prefix, creator), offset = offset, limit = limit, reverse = True)
    id_list   = log_list_to_id_list(log_list)
    note_dict = batch_query(id_list)
    files     = []

    for id in id_list:
        note = note_dict.get(id)
        if note:
            files.append(note)
    fill_parent_name(files)
    return files

@xutils.timeit(name = "NoteDao.ListRecentViewed", logfile = True, logargs = True)
def list_recent_viewed(creator = None, offset = 0, limit = 10):
    if limit is None:
        limit = xconfig.PAGE_SIZE

    user = xauth.current_name()
    if user is None:
        user = "public"
    return list_note_by_log("note_visit_log", creator, offset, limit)

@xutils.timeit(name = "NoteDao.ListRecentEdit:leveldb", logfile = True, logargs = True)
def list_recent_edit(creator = None, offset = 0, limit = None):
    """通过KV存储实现"""
    if limit is None:
        limit = xconfig.PAGE_SIZE
    
    return list_note_by_log("note_edit_log", creator, offset, limit)

def list_recent_events(creator = None, offset = 0, limit = None):
    create_events = list_recent_created(creator, offset, limit)
    edit_events = list_recent_edit(creator, offset, limit)
    view_events = list_recent_viewed(creator, offset, limit)

    def map_notes(notes, action):
        for note in notes:
            note.action = action
            if action == "create":
                note.action_time = note.ctime
            elif action == "edit":
                note.action_time = note.mtime
            else:
                note.action_time = note.atime

    map_notes(create_events, "create")
    map_notes(edit_events, "edit")
    map_notes(view_events, "view")

    events = create_events + edit_events + view_events
    events.sort(key = lambda x: x.action_time, reverse = True)
    return events[offset: offset + limit]


def list_most_visited(creator, offset, limit):
    logs = list_note_by_log("note_visit_log", creator)
    logs.sort(key = lambda x: x.visited_cnt, reverse = True)
    return logs[offset:offset+limit]

def list_hot(creator, offset, limit):
    if limit < 0:
        limit = MAX_VIEW_LOG
    logs = list_note_by_log("note_visit_log", creator)
    logs.sort(key = lambda x: x.hot_index or 0, reverse = True)
    return logs[offset:offset+limit]

def list_by_date(field, creator, date):
    user = creator
    if user is None:
        user = "public"

    def list_func(key, value):
        if value.is_deleted:
            return False
        return date in getattr(value, field)
    
    files = dbutil.prefix_list("note_tiny:%s" % user, list_func)
    fill_parent_name(files)
    return files

@xutils.timeit(name = "NoteDao.CountNote", logfile=True, logargs=True, logret=True)
def count_by_creator(creator):
    def count_func(key, value):
        if value.is_deleted:
            return False
        return value.creator == creator and type != 'group'
    return dbutil.prefix_count("note_tiny:%s" % creator, count_func)

def count_user_note(creator):
    return count_by_creator(creator)

def count_ungrouped(creator):
    return count_ungrouped(creator, 0)

@xutils.timeit(name = "NoteDao.CountNoteByParent", logfile = True, logargs = True, logret = True)
def count_by_parent(creator, parent_id):
    """统计笔记数量
    @param {string} creator 创建者
    @param {string/number} parent_id 父级节点ID
    """
    # TODO 添加索引优化
    def list_note_func(key, value):
        if value.is_deleted:
            return False
        return (value.is_public or value.creator == creator) and str(value.parent_id) == str(parent_id)

    return dbutil.prefix_count("note_tiny", list_note_func)

@xutils.timeit(name = "NoteDao.CountDict", logfile = True, logargs = True, logret = True)
def count_dict(user_name):
    import xtables
    return xtables.get_dict_table().count()

@xutils.timeit(name = "NoteDao.FindPrev", logfile = True)
def find_prev_note(note, user_name):
    parent_id = str(note.parent_id)
    note_name = note.name
    def find_prev_func(key, value):
        if value.is_deleted:
            return False
        return str(value.parent_id) == parent_id and value.name < note_name
    result = dbutil.prefix_list("note_tiny:%s" % user_name, find_prev_func)
    result.sort(key = lambda x:x.name, reverse=True)
    if len(result) > 0:
        return result[0]
    else:
        return None


@xutils.timeit(name = "NoteDao.FindNext", logfile = True)
def find_next_note(note, user_name):
    parent_id = str(note.parent_id)
    note_name = note.name
    def find_next_func(key, value):
        if value.is_deleted:
            return False
        return str(value.parent_id) == parent_id and value.name > note_name
    result = dbutil.prefix_list("note_tiny:%s" % user_name, find_next_func)
    result.sort(key = lambda x:x.name)
    # print([x.name for x in result])
    if len(result) > 0:
        return result[0]
    else:
        return None

def add_history(id, version, note):
    if version is None:
        return
    note['note_id'] = id
    dbutil.put("note_history:%s:%s" % (id, version), note)

def list_history(note_id):
    history_list = dbutil.prefix_list("note_history:%s:" % note_id)
    history_list = sorted(history_list, key = lambda x: x.mtime or "", reverse = True)
    return history_list

def delete_history(note_id, version = None):
    pass


def get_history(note_id, version):
    # note = table.select_first(where = dict(note_id = note_id, version = version))
    return dbutil.get("note_history:%s:%s" % (note_id, version))

def search_name(words, creator = None, parent_id = None):
    words = [word.lower() for word in words]
    if parent_id != None:
        parent_id = str(parent_id)

    def search_func(key, value):
        if value.is_deleted:
            return False
        if parent_id != None and str(value.parent_id) != parent_id:
                return False
        return (value.creator == creator or value.is_public) and textutil.contains_all(value.name.lower(), words)
    result = dbutil.prefix_list("note_tiny:%s" % creator, search_func, 0, -1)
    notes  = [build_note_info(item) for item in result]
    notes.sort(key = lambda x: x.mtime, reverse = True)
    return notes

def search_content(words, creator=None):
    words = [word.lower() for word in words]
    def search_func(key, value):
        if value.content is None:
            return False
        return (value.creator == creator or value.is_public) and textutil.contains_all(value.content.lower(), words)
    result = dbutil.prefix_list("note_full", search_func, 0, -1)
    notes = [build_note_info(item) for item in result]
    sort_notes(notes)
    return notes

def count_removed(creator):
    def count_func(key, value):
        return value.is_deleted and value.creator == creator
    return dbutil.prefix_count("note_tiny:%s" % creator, count_func)

def list_removed(creator, offset, limit):
    def list_func(key, value):
        return value.is_deleted and value.creator == creator
    notes = dbutil.prefix_list("note_tiny:%s" % creator, list_func, offset, limit)
    sort_notes(notes)
    return notes

def doc_filter_func(key, value):
    return value.type in ("md", "text", "html", "post", "log", "plan") and value.is_deleted == 0

def table_filter_func(key, value):
    return value.type in ("csv", "table") and value.is_deleted == 0

def get_filter_func(type, default_filter_func):
    if type == "document" or type == "doc":
        return doc_filter_func
    if type in ("csv", "table"):
        return table_filter_func
    return default_filter_func

def list_by_type(creator, type, offset, limit, orderby = "name", skip_archived = False):
    def list_func(key, value):
        if skip_archived and value.archived:
            return False
        return value.type == type and value.creator == creator and value.is_deleted == 0

    filter_func = get_filter_func(type, list_func)
    notes = dbutil.prefix_list("note_tiny:%s" % creator, filter_func, offset, limit, reverse = True)
    sort_notes(notes, orderby)
    return notes

def count_by_type(creator, type):
    def default_count_func(key, value):
        return value.type == type and value.creator == creator and value.is_deleted == 0
    filter_func = get_filter_func(type, default_count_func)
    return dbutil.prefix_count("note_tiny:%s" % creator, filter_func)

def list_sticky(creator, offset = 0, limit = 1000):
    def list_func(key, value):
        return value.priority > 0 and value.creator == creator and value.is_deleted == 0
    notes = dbutil.prefix_list("note_tiny:%s" % creator, list_func, offset, limit)
    sort_notes(notes)
    return notes

def count_sticky(creator):
    def list_func(key, value):
        return value.priority > 0 and value.creator == creator and value.is_deleted == 0
    return dbutil.prefix_count("note_tiny:%s" % creator, list_func)

def list_archived(creator, offset = 0, limit = 100):
    def list_func(key, value):
        return value.archived and value.creator == creator and value.is_deleted == 0
    notes = dbutil.prefix_list("note_tiny:%s" % creator, list_func, offset, limit)
    sort_notes(notes)
    return notes

def get_tags(creator, note_id):
    key = "note_tags:%s:%s" % (creator, note_id)
    note_tags = dbutil.get(key)
    if note_tags:
        return attrget(note_tags, "tags")
    return None

def update_tags(creator, note_id, tags):
    key = "note_tags:%s:%s" % (creator, note_id)
    dbutil.put(key, Storage(note_id = note_id, tags = tags))

    note = get_by_id(note_id)
    if note != None:
        note.tags = tags
        update_index(note)

def delete_tags(creator, note_id):
    key = "note_tags:%s:%s" % (creator, note_id)
    dbutil.delete(key)

def list_by_tag(user, tagname):
    if user is None:
        user = "public"

    def list_func(key, value):
        if value.tags is None:
            return False
        return tagname in value.tags
    
    tags = dbutil.prefix_list("note_tags:%s" % user, list_func)
    files = []
    for tag in tags:
        note = get_by_id(tag.note_id)
        if note != None:
            files.append(note)
    sort_notes(files)
    return files

def list_tag(user):
    if user is None:
        user = "public"

    tags = dict()
    def list_func(key, value):
        if value.tags is None:
            return False
        for tag in value.tags:
            count = tags.get(tag, 0)
            count += 1
            tags[tag] = count
    
    dbutil.prefix_count("note_tags:%s" % user, list_func)
    
    tag_list = [Storage(name = k, amount = tags[k]) for k in tags]
    tag_list.sort(key = lambda x: -x.amount)
    return tag_list

def list_by_func(creator, list_func, offset, limit):
    notes = dbutil.prefix_list("note_tiny:%s" % creator, list_func, offset, limit, reverse = True)
    fix_notes_info(notes)
    return notes

def list_comments(note_id):
    comments = []
    for key, value in dbutil.prefix_iter("note_comment:%s" % note_id, reverse = True, include_key = True):
        comment = value
        comment['id'] = key
        comments.append(comment)
    return comments

def save_comment(comment):
    timeseq = dbutil.timeseq()

    comment["timeseq"] = timeseq
    key = "note_comment:%s:%s" % (comment["note_id"], timeseq)
    dbutil.put(key, comment)

    key2 = "comment_index:%s:%s" % (comment["user"], timeseq)
    comment_index = comment.copy()
    dbutil.put(key2, comment_index)

def delete_comment(comment_id):
    dbutil.delete(comment_id)

def get_comment(comment_id):
    return dbutil.get(comment_id)

def add_search_history(user, search_key, category = "default", cost_time = 0):
    key = "search_history:%s:%s" % (user, dbutil.timeseq())
    dbutil.put(key, Storage(key = search_key, category = category, cost_time = cost_time))

def list_search_history(user, limit = 1000, orderby = "time_desc"):
    if user is None or user == "":
        return []
    return dbutil.prefix_list("search_history:%s" % user, reverse = True, limit = limit)

def refresh_note_stat(user_name):
    stat = Storage()

    if user_name is None:
        return stat

    stat.total         = count_by_creator(user_name)
    stat.group_count   = count_group(user_name)
    stat.doc_count     = count_by_type(user_name, "doc")
    stat.gallery_count = count_by_type(user_name, "gallery")
    stat.list_count    = count_by_type(user_name, "list")
    stat.table_count   = count_by_type(user_name, "table")
    stat.plan_count    = count_by_type(user_name, "plan")
    stat.log_count     = count_by_type(user_name, "log")
    stat.sticky_count  = count_sticky(user_name)
    stat.removed_count = count_removed(user_name)
    stat.dict_count    = count_dict(user_name)

    dbutil.put("user_stat:%s:note" % user_name, stat)
    return stat


def get_note_stat(user_name):
    stat = dbutil.get("user_stat:%s:note" % user_name)
    if stat is None:
        stat = refresh_note_stat(user_name)
    return stat

# write functions
xutils.register_func("note.create", create_note)
xutils.register_func("note.update", update_note)
xutils.register_func("note.update0", update0)
xutils.register_func("note.update_index", update_index)
xutils.register_func("note.move", move_note)
xutils.register_func("note.visit",  visit_note)
xutils.register_func("note.delete", delete_note)
xutils.register_func("note.touch",  touch_note)
xutils.register_func("note.update_tags", update_tags)
xutils.register_func("note.create_token", create_token)

# query functions
xutils.register_func("note.get_root", get_root)
xutils.register_func("note.get_default_group", get_default_group)
xutils.register_func("note.get_by_id", get_by_id)
xutils.register_func("note.get_by_token", get_by_token)
xutils.register_func("note.get_by_id_creator", get_by_id_creator)
xutils.register_func("note.get_by_name", get_by_name)
xutils.register_func("note.get_tags", get_tags)
xutils.register_func("note.search_name", search_name)
xutils.register_func("note.search_content", search_content)

# list functions
xutils.register_func("note.list_path", list_path)
xutils.register_func("note.list_group", list_group)
xutils.register_func("note.list_default_notes", list_default_notes)
xutils.register_func("note.list_root_group", list_root_group)
xutils.register_func("note.list_by_parent", list_by_parent)
xutils.register_func("note.list_by_date", list_by_date)
xutils.register_func("note.list_by_tag", list_by_tag)
xutils.register_func("note.list_by_type", list_by_type)
xutils.register_func("note.list_removed", list_removed)
xutils.register_func("note.list_sticky",  list_sticky)
xutils.register_func("note.list_archived", list_archived)
xutils.register_func("note.list_tag", list_tag)
xutils.register_func("note.list_public", list_public)
xutils.register_func("note.list_recent_created", list_recent_created)
xutils.register_func("note.list_recent_edit", list_recent_edit)
xutils.register_func("note.list_recent_viewed", list_recent_viewed)
xutils.register_func("note.list_recent_events", list_recent_events)
xutils.register_func("note.list_most_visited", list_most_visited)
xutils.register_func("note.list_hot", list_hot)
xutils.register_func("note.list_by_func", list_by_func)

# count functions
xutils.register_func("note.count_public", count_public)
xutils.register_func("note.count_recent_edit", count_user_note)
xutils.register_func("note.count_user_note", count_user_note)
xutils.register_func("note.count_ungrouped", count_ungrouped)
xutils.register_func("note.count_removed", count_removed)
xutils.register_func("note.count_by_type", count_by_type)
xutils.register_func("note.count_by_parent",  count_by_parent)

# others
xutils.register_func("note.find_prev_note", find_prev_note)
xutils.register_func("note.find_next_note", find_next_note)

# history
xutils.register_func("note.add_history", add_history)
xutils.register_func("note.list_history", list_history)
xutils.register_func("note.get_history", get_history)
xutils.register_func("note.add_search_history", add_search_history)
xutils.register_func("note.list_search_history", list_search_history)

# comments
xutils.register_func("note.list_comments", list_comments)
xutils.register_func("note.get_comment",  get_comment)
xutils.register_func("note.save_comment", save_comment)
xutils.register_func("note.delete_comment", delete_comment)

# stat
xutils.register_func("note.get_note_stat", get_note_stat)



