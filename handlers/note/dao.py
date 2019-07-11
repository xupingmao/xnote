# encoding=utf-8
# Created by xupingmao on 2017/04/16
# @modified 2019/07/08 23:25:56

"""资料的DAO操作集合

由于sqlite是单线程，所以直接使用方法操作
如果是MySQL等数据库，使用 threadeddict 来操作，直接用webpy的ctx
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
from xutils import readfile, savetofile, sqlite3, Storage
from xutils import dateutil, cacheutil, Timer, dbutil, textutil, fsutil

MAX_VISITED_CNT = 200
readFile        = readfile
config          = xconfig
DB_PATH         = config.DB_PATH


class FileDO(dict):
    """This class behaves like both object and dict"""
    def __init__(self, name):
        self.id          = None
        self.related     = ''
        self.size        = 0
        now = dateutil.format_time()
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

def query_note_conent(id):
    db = xtables.get_note_content_table()
    result = db.select_first(where=dict(id=id))
    if result is None:
        return None, None
    return result.get("content", ""), result.get("data", "")

def query_note_name(id):
    db = xtables.get_note_table()
    result = db.select_first(what = "name", where = dict(id = id))
    if result:
        return result.name
    return None

def batch_query_sqlite(id_list):
    db = xtables.get_note_table()
    result = db.select(where = "id IN $id_list", vars = dict(id_list = id_list))
    dict_result = dict()
    for item in result:
        dict_result[item.id] = item
    return dict_result

def batch_query(id_list):
    if xconfig.DB_ENGINE == "sqlite":
        return batch_query_sqlite(id_list)

    creator = xauth.current_name()
    result = dict()
    for id in id_list:
        note = dbutil.get("note_tiny:%s:%020d" % (creator, int(id)))
        if note:
            result[id] = note
    return result

def sort_notes(notes, orderby = "mtime_desc"):
    if orderby == "name":
        notes.sort(key = lambda x: x.name)
    else:
        # mtime_desc
        notes.sort(key = lambda x: x.mtime, reverse = True)
    notes.sort(key = lambda x: x.priority, reverse = True)
    for note in notes:
        note.url = "/note/view?id=%s" % note.id

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
    note.url = "/note/view?id={}".format(dict["id"])
    return note


def to_sqlite_obj(text):
    if text is None:
        return "NULL"
    if not isinstance(text, six.string_types):
        return repr(text)
    text = text.replace("'", "''")
    return "'" + text + "'"


class TableDesc:
    def __init__(self, row = None):
        if row != None:
            self.name = row[0]
            self.items = []
        else:
            self.name = ""
            self.items = []
    
    def __repr__(self):
        return "%s :{\n%s\n}" % (self.name, self.items)

class RowDesc:
    def __init__(self, row):
        self.name = row['name']
        self.type = row['type']
        self.defaultValue = row['dflt_value']
        self.notNull = row['notnull']
        self.primaryKey = row['pk']

    def __repr__(self):
        return "%s : %s\n" % (self.name, self.type)


def get_file_db():
    return xtables.get_file_table()

@xutils.timeit(name = "NoteDao.ListPath:leveldb", logfile = True)
def list_path(file, limit = 2):
    pathlist = []
    while file is not None:
        pathlist.insert(0, file)
        file.url = "/note/view?id=%s" % file.id
        if len(pathlist) >= limit:
            break
        if file.parent_id == 0:
            break
        else:
            file = get_by_id(file.parent_id, include_full = False)
    return pathlist

@xutils.timeit(name = "NoteDao.GetById:leveldb", logfile = True)
def get_by_id(id, db=None, include_full = True):
    note = dbutil.get("note_full:%s" % id)
    if note and not include_full:
        del note.content
        del note.data
    if note:
        note.url = "/note/view?id=%s" % note.id
    return note

def get_by_id_creator(id, creator, db=None):
    note = get_by_id(id)
    if note and note.creator == creator:
        return note
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
    
    # 更新分组下面页面的数量 TODO
    update_children_count(note_dict["parent_id"])

    xmanager.fire("note.add", dict(name=name, type=type))

    # 创建对应的文件夹
    if type != "group":
        dirname = os.path.join(xconfig.UPLOAD_DIR, creator, str(parent_id), str(note_id))
    else:
        dirname = os.path.join(xconfig.UPLOAD_DIR, creator, str(note_id))
    xutils.makedirs(dirname)

    return note_id

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
    if "path" in note:
        del note["path"]
    if "url" in note:
        del note["url"]

    dbutil.put("note_full:%s" % note_id, note)

    # 更新笔记的排序
    update_note_rank(note)

    del note['content']
    del note['data']
    dbutil.put("note_tiny:%s:%020d" % (note.creator, int(note_id)), note)

    if note.type == "group":
        # 笔记本的索引
        dbutil.put("notebook:%s:%020d" % (note.creator, int(note_id)), note)

def touch_note(note_id):
    note = get_by_id(note_id)
    if note != None:
        note.mtime = dateutil.format_datetime()
        kv_put_note(note_id, note)

def update_note(where, **kw):
    note_id   = where['id']
    creator   = where.get('creator')
    content   = kw.get('content')
    data      = kw.get('data')
    priority  = kw.get('priority')
    name      = kw.get("name")
    atime     = kw.get("atime")
    parent_id = kw.get("parent_id")
    is_public = kw.get("is_public")
    tags      = kw.get("tags")

    old_parent_id = None
    new_parent_id = None

    note = get_by_id(note_id)
    if note:
        if creator and note.creator != creator:
            return 0
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
        if parent_id != None:
            old_parent_id  = note.parent_id
            new_parent_id  = parent_id
            note.parent_id = parent_id
        if is_public != None:
            note.is_public = is_public
        if tags != None:
            note.tags = tags

        note.mtime   = xutils.format_time()
        note.version += 1
        
        # 只修改优先级
        if len(kw) == 1 and kw.get('priority') != None:
            note.version -= 1
        # 只修改名称
        if len(kw) == 1 and kw.get('name') != None:
            note.version -= 1

        kv_put_note(note_id, note)

        # 处理移动分类时的统计
        if new_parent_id != None and new_parent_id != old_parent_id:
            update_children_count(old_parent_id)
            update_children_count(new_parent_id)
            old_dirname = os.path.join(xconfig.UPLOAD_DIR, note.creator, str(old_parent_id), str(note.id))
            new_dirname = os.path.join(xconfig.UPLOAD_DIR, note.creator, str(new_parent_id), str(note.id))
            fsutil.mvfile(old_dirname, new_dirname)
        # 更新parent更新时间
        touch_note(note.parent_id)
        return 1
    return 0


def get_by_name(name, db = None):
    def find_func(key, value):
        if value.is_deleted:
            return False
        return value.name == name
    result = dbutil.prefix_list("note:", find_func, 0, 1)
    if len(result) > 0:
        note = result[0]
        note.url = "/note/view?id=%s" % note.id
        return note
    return None

def visit_note(id):
    note = get_by_id(id)
    if note:
        note.atime = xutils.format_datetime()
        if note.visited_cnt is None:
            note.visited_cnt = 0
        note.visited_cnt += 1
        kv_put_note(id, note)

def delete_note(id):
    note = get_by_id(id)
    if note:
        note.mtime = xutils.format_datetime()
        note.is_deleted = 1
        kv_put_note(id, note)
        update_children_count(note.parent_id)

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
    children_count = count_note(creator, parent_id)
    note.size      = children_count

    kv_put_note(note.id, note)
        
def get_db():
    return get_file_db()

def get_table_struct(table_name):
    rs = get_db().execute("pragma table_info('%s')" % table_name)
    result = []
    for item in rs:
        result.append(item)
    return result

def fill_parent_name(files):
    id_list = []
    for item in files:
        id_list.append(item.parent_id)

    note_dict = batch_query(id_list)
    for item in files:
        parent = note_dict.get(item.parent_id)
        if parent != None:
            item.parent_name = parent.name
        else:
            item.parent_name = None

@xutils.timeit(name = "NoteDao.ListGroup:leveldb", logfile = True)
def kv_list_group(creator = None):
    # TODO 添加索引优化
    def list_group_func(key, value):
        return value.type == "group" and value.creator == creator and value.is_deleted == 0

    notes = dbutil.prefix_list("note_tiny:", list_group_func)
    sort_notes(notes, "mtime_desc")
    return notes

def list_group(current_name = None):
    if current_name is None:
        current_name = str(xauth.get_current_name())

    return kv_list_group(current_name)

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
def kv_list_by_parent(creator, parent_id, offset, limit, orderby="mtime_desc"):
    parent_id = str(parent_id)
    # TODO 添加索引优化
    def list_note_func(key, value):
        if value.is_deleted:
            return False
        if value.type == "group":
            return False
        return (value.is_public or value.creator == creator) and str(value.parent_id) == parent_id

    notes = dbutil.prefix_list("note_tiny:", list_note_func)
    sort_notes(notes, orderby)
    return notes[offset:offset+limit]

def list_by_parent(*args):
    return kv_list_by_parent(*args)

@xutils.timeit(name = "NoteDao.ListRecentCreated", logfile = True)
def list_recent_created(parent_id = None, offset = 0, limit = 10):
    def list_func(key, value):
        return value.is_deleted != 1

    creator = xauth.current_name()
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
def list_recent_edit(parent_id = None, offset=0, limit=None):
    """通过KV存储实现"""
    if limit is None:
        limit = xconfig.PAGE_SIZE

    user = xauth.current_name()
    if user is None:
        user = "public"
    
    id_list   = dbutil.zrange("note_recent:%s" % user, -offset-1, -offset-limit)
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

def list_by_tag(user, tagname):
    if user is None:
        user = "public"

    def list_func(key, value):
        if value.is_deleted:
            return False
        if value.tags is None:
            return False
        return tagname in value.tags
    
    files = dbutil.prefix_list("note_tiny:%s" % user, list_func)
    sort_notes(files)
    return files

@xutils.timeit(name = "NoteDao.CountNote", logfile=True, logargs=True, logret=True)
def count_user_note(creator):
    if xconfig.DB_ENGINE == "sqlite":
        db    = xtables.get_file_table()
        where = "is_deleted = 0 AND creator = $creator AND type != 'group'"
        count = db.count(where, vars = dict(creator = xauth.get_current_name()))
    else:
        def count_func(key, value):
            if value.is_deleted:
                return False
            return value.creator == creator and type != 'group'
        count = dbutil.prefix_count("note_tiny:%s" % creator, count_func)
    return count

def count_ungrouped(creator):
    t = Timer()
    t.start()
    count_key = "%s@note.ungrouped.count" % creator
    count = cacheutil.get(count_key)
    if count is None:
        count = xtables.get_file_table().count(where="creator=$creator AND parent_id=0 AND is_deleted=0 AND type!='group'", 
            vars=dict(creator=creator))
        xutils.cache_put(count_key, count, expire=600)
    t.stop()
    xutils.trace("NoteDao.CountUngrouped", "", t.cost_millis())
    return count

@xutils.timeit(name = "NoteDao.CountNote", logfile = True, logargs = True, logret = True)
def count_note(creator, parent_id):
    if xconfig.DB_ENGINE == "sqlite":
        db = xtables.get_note_table()
        where_sql = "parent_id=$parent_id AND is_deleted=0 AND (creator=$creator OR is_public=1)"
        amount    = db.count(where = where_sql,
                    vars=dict(parent_id=parent_id, creator=creator))
        return amount
    else:
        # TODO 添加索引优化
        def list_note_func(key, value):
            if value.is_deleted:
                return False
            if value.type == "group":
                return False
            return (value.is_public or value.creator == creator) and str(value.parent_id) == str(parent_id)

        return dbutil.prefix_count("note_tiny", list_note_func)


def list_tag(user):
    if user is None:
        user = "public"

    tags = dict()
    def list_func(key, value):
        if value.is_deleted:
            return False
        if value.tags is None:
            return False
        for tag in value.tags:
            count = tags.get(tag, 0)
            count += 1
            tags[tag] = count
    
    dbutil.prefix_count("note_tiny:%s" % user, list_func)
    
    tag_list = [Storage(name = k, amount = tags[k]) for k in tags]
    tag_list.sort(key = lambda x: -x.amount)
    return tag_list

@xutils.timeit(name = "NoteDao.FindPrev", logfile = True)
def find_prev_note(note):
    # where = "parent_id = $parent_id AND name < $name ORDER BY name DESC LIMIT 1"
    # table = xtables.get_file_table()
    # return table.select_first(where = where, vars = dict(name = note.name, parent_id = note.parent_id))
    parent_id = str(note.parent_id)
    note_name = note.name
    def find_prev_func(key, value):
        if value.is_deleted:
            return False
        return str(value.parent_id) == parent_id and value.name < note_name
    result = dbutil.prefix_list("note_tiny:%s" % note.creator, find_prev_func)
    result.sort(key = lambda x:x.name, reverse=True)
    if len(result) > 0:
        return result[0]
    else:
        return None


@xutils.timeit(name = "NoteDao.FindNext", logfile = True)
def find_next_note(note):
    # where = "parent_id = $parent_id AND name > $name ORDER BY name ASC LIMIT 1"
    # table = xtables.get_file_table()
    # return table.select_first(where = where, vars = dict(name = note.name, parent_id = note.parent_id))
    parent_id = str(note.parent_id)
    note_name = note.name
    def find_next_func(key, value):
        if value.is_deleted:
            return False
        return str(value.parent_id) == parent_id and value.name > note_name
    result = dbutil.prefix_list("note_tiny:%s" % note.creator, find_next_func)
    result.sort(key = lambda x:x.name)
    # print([x.name for x in result])
    if len(result) > 0:
        return result[0]
    else:
        return None

def update_priority(creator, id, value):
    table = xtables.get_file_table()
    rows = table.update(priority = value, where = dict(creator = creator, id = id))
    cache_key = "[%s]note.recent" % creator
    cacheutil.prefix_del(cache_key)
    return rows > 0

def add_history(id, version, note):
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

def list_by_type(creator, type, offset, limit):
    def list_func(key, value):
        return value.type == type and value.creator == creator and value.is_deleted == 0
    notes = dbutil.prefix_list("note_tiny:%s" % creator, list_func, offset, limit)
    sort_notes(notes)
    return notes

def count_by_type(creator, type):
    def count_func(key, value):
        return value.type == type and value.creator == creator and value.is_deleted == 0
    return dbutil.prefix_count("note_tiny:%s" % creator, count_func)

def list_sticky(creator):
    def list_func(key, value):
        return value.priority > 0 and value.creator == creator and value.is_deleted == 0
    notes = dbutil.prefix_list("note_tiny:%s" % creator, list_func)
    sort_notes(notes)
    return notes

xutils.register_func("note.create", create_note)
xutils.register_func("note.update", update_note)
xutils.register_func("note.visit",  visit_note)
xutils.register_func("note.count",  count_note)
xutils.register_func("note.delete", delete_note)
xutils.register_func("note.get_by_id", get_by_id)
xutils.register_func("note.get_by_name", get_by_name)
xutils.register_func("note.get_by_id_creator", get_by_id_creator)
xutils.register_func("note.search_name", search_name)
xutils.register_func("note.search_content", search_content)

# list functions
xutils.register_func("note.list_path", list_path)
xutils.register_func("note.list_group", list_group)
xutils.register_func("note.list_note",  list_by_parent)
xutils.register_func("note.list_by_parent", list_by_parent)
xutils.register_func("note.list_tag", list_tag)
xutils.register_func("note.list_public", list_public)
xutils.register_func("note.list_recent_created", list_recent_created)
xutils.register_func("note.list_recent_edit", list_recent_edit)
xutils.register_func("note.list_recent_viewed", list_recent_viewed)
xutils.register_func("note.list_by_date", list_by_date)
xutils.register_func("note.list_by_tag", list_by_tag)
xutils.register_func("note.list_removed", list_removed)
xutils.register_func("note.list_by_type", list_by_type)
xutils.register_func("note.list_sticky",  list_sticky)

# count functions
xutils.register_func("note.count_public", count_public)
xutils.register_func("note.count_recent_edit", count_user_note)
xutils.register_func("note.count_user_note", count_user_note)
xutils.register_func("note.count_ungrouped", count_ungrouped)
xutils.register_func("note.count_removed", count_removed)
xutils.register_func("note.count_by_type", count_by_type)

xutils.register_func("note.find_prev_note", find_prev_note)
xutils.register_func("note.find_next_note", find_next_note)
xutils.register_func("note.update_priority", update_priority)
xutils.register_func("note.add_history", add_history)
xutils.register_func("note.list_history", list_history)
xutils.register_func("note.get_history", get_history)

