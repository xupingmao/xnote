# encoding=utf-8
# Created by xupingmao on 2017/04/16
# @modified 2020/02/02 14:46:54

"""资料的DAO操作集合
DAO层只做最基础的数据库交互，不做权限校验（空校验要做），业务状态检查之类的工作

一些表的说明
note_full:<note_id>              = 笔记的内容，包含一些属性（部分属性比如访问时间、访问次数不是实时更新的）
note_index:<note_id>             = 笔记索引
note_tiny:<user>:<note_id>       = 用户维度的笔记索引
note_book:<user>:<note_id>       = 用户维度的笔记本(项目)索引
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
from xutils import readfile, savetofile, sqlite3, Storage
from xutils import dateutil, cacheutil, Timer, dbutil, textutil, fsutil
from xutils import attrget

MAX_VISITED_CNT = 200
DB_PATH         = xconfig.DB_PATH
NOTE_ICON_DICT = {
    "group"   : "fa-folder orange",
    "csv"     : "fa-table",
    "table"   : "fa-table",
    "post"    : "fa-file-word-o",
    "html"    : "fa-file-word-o",
    "gallery" : "fa-photo",
    "list"    : "fa-list"
}

class FileDO(dict):
    """This class behaves like both object and dict"""
    def __init__(self, name):
        self.id          = None
        self.related     = ''
        self.size        = 0
        now              = dateutil.format_time()
        self.mtime       = now
        self.atime       = now
        self.ctime       = now
        self.visited_cnt = 0
        self.name        = name

    def __getattr__(self, key): 
        try:
            return self[key]
        except KeyError as k:
            # raise AttributeError(k)
            return None
    
    def __setattr__(self, key, value): 
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError as k:
            raise AttributeError(k)
    
    @staticmethod
    def fromDict(dict, option=None):
        """build fileDO from dict"""
        name = dict['name']
        file = FileDO(name)
        for key in dict:
            file[key] = dict[key]
            # setattr(file, key, dict[key])
        if file.get("content", None) is None:
            file.content = ""
        if option:
            file.option = option
        file.url = "/note/view?id={}".format(dict["id"])
        return file

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

def batch_query(id_list):
    creator = xauth.current_name()
    result = dict()
    for id in id_list:
        note = dbutil.get("note_tiny:%s:%020d" % (creator, int(id)))
        if note:
            result[id] = note
    return result

def sort_notes(notes, orderby = "name"):
    if orderby == "name":
        notes.sort(key = lambda x: x.name)
    elif orderby == "name_desc":
        notes.sort(key = lambda x: x.name, reverse = True)
    else:
        # mtime_desc
        notes.sort(key = lambda x: x.mtime, reverse = True)
    # 置顶笔记
    notes.sort(key = lambda x: x.priority, reverse = True)
    # 文件夹放在前面
    notes.sort(key = lambda x: 0 if x.type == "group" else 1)
    fix_notes_info(notes)

def build_note(dict):
    id   = dict['id']
    name = dict['name']
    note = FileDO(name)
    for key in dict:
        note[key] = dict[key]
        # setattr(file, key, dict[key])
    if note.get("content", None) is None:
        note.content = ""
    content, data = query_note_conent(id)
    if content is not None:
        note.content = content
    if data is not None:
        note.data = data
    build_note_info(note)
    return note

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

@xutils.timeit(name = "NoteDao.ListPath:leveldb", logfile = True)
def list_path(file, limit = 2):
    pathlist = []
    while file is not None:
        pathlist.insert(0, file)
        file.url = "/note/%s" % file.id
        if len(pathlist) >= limit:
            break
        if str(file.id) == "0":
            break
        if str(file.parent_id) == "0":
            pathlist.insert(0, get_root())
            break
        else:
            file = get_by_id(file.parent_id, include_full = False)
    return pathlist

@xutils.timeit(name = "NoteDao.GetById:leveldb", logfile = True)
def get_by_id(id, include_full = True):
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

def create_note(note_dict):
    content   = note_dict["content"]
    data      = note_dict["data"]
    creator   = note_dict["creator"]
    priority  = note_dict["priority"]
    mtime     = note_dict["mtime"]
    parent_id = note_dict.get("parent_id", "0")
    name      = note_dict.get("name")

    note_id = dbutil.timeseq()
    note_dict["id"] = note_id
    kv_put_note(note_id, note_dict)
    
    # 更新分组下面页面的数量
    update_children_count(note_dict["parent_id"])

    xmanager.fire("note.add", dict(name=name, type=type))

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

def update_note_rank(note):
    mtime = note.mtime
    atime = note.atime
    creator = note.creator
    note_id = note.id
    
    if note.is_deleted:
        dbutil.zrem("note_recent:%s" % creator, note_id)
        dbutil.zrem("note_visit:%s" % creator, note_id)
        dbutil.zrem("note_recent:public", note_id)
    elif note.type != "group":
        # 分组不需要记录
        dbutil.zadd("note_recent:%s" % creator, mtime, note_id)
        dbutil.zadd("note_visit:%s" % creator, atime, note_id)
        if note.is_public:
            dbutil.zadd("note_recent:public", mtime, note_id)

def kv_put_note(note_id, note):
    priority = note.priority
    mtime    = note.mtime
    creator  = note.creator
    atime    = note.atime

    # 删除不需要持久化的数据
    del_dict_key(note, "path")
    del_dict_key(note, "url")
    del_dict_key(note, "icon")

    dbutil.put("note_full:%s" % note_id, note)

    # 更新索引
    update_index(note)

def touch_note(note_id):
    note = get_by_id(note_id)
    if note != None:
        note.mtime = dateutil.format_datetime()
        update_index(note)

def del_dict_key(dict, key):
    if key in dict:
        del dict[key]

def update_index(note):
    """更新索引的时候也会更新用户维度的索引(note_tiny)"""
    id = note['id']

    note_index = Storage(**note)

    del_dict_key(note_index, 'path')
    del_dict_key(note_index, 'url')
    del_dict_key(note_index, 'icon')
    del_dict_key(note_index, 'data')
    del_dict_key(note_index, 'content')

    dbutil.put('note_index:%s' % id, note_index)
    
    # 更新笔记的排序
    update_note_rank(note)
    # 更新用户索引
    dbutil.put("note_tiny:%s:%020d" % (note.creator, int(id)), note)

    if note.type == "group":
        dbutil.put("notebook:%s:%020d" % (note.creator, int(id)), note)

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

        old_version  = note.version
        note.mtime   = xutils.format_time()
        note.version += 1
        
        # 只修改优先级
        if len(kw) == 1 and kw.get('priority') != None:
            note.version = old_version
        # 只修改名称
        if len(kw) == 1 and kw.get('name') != None:
            note.version = old_version

        kv_put_note(note_id, note)
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
    kv_put_note(note.id, note)

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

def visit_note(id):
    note = get_by_id(id)
    if note:
        note.atime = xutils.format_datetime()
        if note.visited_cnt is None:
            note.visited_cnt = 0
        note.visited_cnt += 1
        update_index(note)

def delete_note(id):
    note = get_by_id(id)
    if note is None:
        return

    if note.is_deleted != 0:
        # 已经被删除了，执行物理删除
        tiny_key = "note_tiny:%s:%s" % (note.creator, note.id)
        full_key = "note_full:%s" % note.id
        index_key = "note_index:%s" % note.id
        dbutil.delete(tiny_key)
        dbutil.delete(full_key)
        dbutil.delete(index_key)
        return

    # 标记删除
    note.mtime = xutils.format_datetime()
    note.is_deleted = 1
    kv_put_note(id, note)

    # 更新数量
    update_children_count(note.parent_id)
    delete_tags(note.creator, id)

    # 删除笔记本
    book_key = "notebook:%s:%020d" % (note.creator, int(id))
    dbutil.delete(book_key)

    # 更新数量统计
    refresh_note_stat(note.creator)

def get_vpath(record):
    pathlist = []
    current = record
    db = FileDB()
    while current is not None:
        pathlist.append(current)
        if current.parent_id is not None and current.parent_id != "":
            current = get_by_id(current.parent_id, db)
        else:
            current = None

    pathlist.reverse()
    return pathlist

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
        if skip_archived and value.parent_id != 0:
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
def list_by_parent(creator, parent_id, offset = 0, limit = 1000, orderby="name"):
    parent_id = str(parent_id)
    # TODO 添加索引优化
    def list_note_func(key, value):
        if value.is_deleted:
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

@xutils.timeit(name = "NoteDao.ListRecentViewed", logfile = True, logargs = True)
def list_recent_viewed(creator = None, offset = 0, limit = 10):
    if limit is None:
        limit = xconfig.PAGE_SIZE

    user = xauth.current_name()
    if user is None:
        user = "public"
    
    id_list   = dbutil.zrange("note_visit:%s" % user, -offset-1, -offset-limit)
    note_dict = batch_query(id_list)
    files     = []

    for id in id_list:
        note = note_dict.get(id)
        if note:
            files.append(note)
    fill_parent_name(files)
    return files

@xutils.timeit(name = "NoteDao.ListRecentEdit:leveldb", logfile = True, logargs = True)
def list_recent_edit(creator = None, offset=0, limit=None):
    """通过KV存储实现"""
    if limit is None:
        limit = xconfig.PAGE_SIZE
    
    id_list   = dbutil.zrange("note_recent:%s" % creator, -offset-1, -offset-limit)
    note_dict = batch_query(id_list)
    files     = []

    for id in id_list:
        note = note_dict.get(id)
        if note:
            files.append(note)
    fill_parent_name(files)
    return files

def list_most_visited(creator):
    pass

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
    # history_list = table.select(where=dict(note_id=note_id), order="mtime DESC")
    return history_list

def get_history(note_id, version):
    # note = table.select_first(where = dict(note_id = note_id, version = version))
    return dbutil.get("note_history:%s:%s" % (note_id, version))

def file_wrapper(dict, option=None):
    """build fileDO from dict"""
    name = dict['name']
    file = Storage()
    for key in dict:
        file[key] = dict[key]
        # setattr(file, key, dict[key])
    if hasattr(file, "content") and file.content is None:
        file.content = ""
    if option:
        file.option = option
    file.url = "/note/view?id={}".format(dict["id"])
    # 文档类型，和文件系统file区分
    file.category = "note"
    return file

def search_name(words, creator=None):
    words = [word.lower() for word in words]
    def search_func(key, value):
        if value.is_deleted:
            return False
        return (value.creator == creator or value.is_public) and textutil.contains_all(value.name.lower(), words)
    result = dbutil.prefix_list("note_tiny", search_func, 0, -1)
    notes  = [file_wrapper(item) for item in result]
    notes.sort(key = lambda x: x.mtime, reverse = True)
    return notes

def search_content(words, creator=None):
    words = [word.lower() for word in words]
    def search_func(key, value):
        if value.content is None:
            return False
        return (value.creator == creator or value.is_public) and textutil.contains_all(value.content.lower(), words)
    result = dbutil.prefix_list("note_full", search_func, 0, -1)
    notes = [file_wrapper(item) for item in result]
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
    return value.type in ("md", "text", "html", "post") and value.is_deleted == 0

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
xutils.register_func("note.move", move_note)
xutils.register_func("note.visit",  visit_note)
xutils.register_func("note.delete", delete_note)
xutils.register_func("note.touch",  touch_note)
xutils.register_func("note.update_tags", update_tags)
xutils.register_func("note.create_token", create_token)

# query functions
xutils.register_func("note.get_root", get_root)
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



