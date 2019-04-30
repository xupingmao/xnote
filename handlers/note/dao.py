# encoding=utf-8
# Created by xupingmao on 2017/04/16
# @modified 2019/04/30 22:42:02

"""资料的DAO操作集合

由于sqlite是单线程，所以直接使用方法操作
如果是MySQL等数据库，使用 threadeddict 来操作，直接用webpy的ctx
"""
import time
import math
import re
import six
import web.db as db
import xconfig
import xtables
import xutils
import xauth
from xutils import readfile, savetofile, sqlite3, Storage
from xutils import dateutil, cacheutil, Timer, dbutil, textutil

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
        t                = dateutil.get_seconds()
        self.mtime       = t
        self.atime       = t
        self.ctime       = t
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
    result = dict()
    for id in id_list:
        note = dbutil.get("note_full:%s" % id)
        if note:
            result[id] = note
    return result

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

@xutils.timeit(name = "NoteDao.ListPath:sqlite", logfile = True)
def list_path_old(file, limit = 2, db = None):
    if db is None:
        db = xtables.get_file_table()
    pathlist = []
    while file is not None:
        pathlist.insert(0, file)
        file.url = "/note/view?id=%s" % file.id
        if len(pathlist) >= limit:
            break
        if file.parent_id == 0:
            break
        else:
            file = db.select_first(what="id,name,type,creator", where=dict(id=file.parent_id))
    return pathlist

@xutils.timeit(name = "NoteDao.ListPath:leveldb", logfile = True)
def list_path(file, limit = 2):
    if xconfig.DB_ENGINE == "sqlite":
        return list_path_old(file, limit)
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

@xutils.timeit(name = "NoteDao.GetById:sqlite", logfile = True)
def get_by_id_old(id, db=None):
    if db is None:
        db = get_file_db()
    first = db.select_first(where=dict(id=id))
    if first is not None:
        return build_note(first)
    return None

@xutils.timeit(name = "NoteDao.GetById:leveldb", logfile = True)
def get_by_id(id, db=None, include_full = True):
    if xconfig.DB_ENGINE == "sqlite":
        return get_by_id_old(id, db)
    note = dbutil.get("note_full:%s" % id)
    if note and not include_full:
        del note.content
        del note.data
    return note

def get_by_id_creator(id, creator, db=None):
    note = get_by_id(id)
    if note and note.creator == creator:
        return note
    return None

def update_note_content(id, content, data=''):
    if id is None:
        return
    if content is None:
        content = ''
    if data is None:
        data = ''
    db = xtables.get_note_content_table()
    result = db.select_first(where=dict(id=id))
    if result is None:
        db.insert(id=id, content=content, data=data)
    else:
        db.update(where=dict(id=id), 
            content=content,
            data = data)

def create_note(note_dict):
    content  = note_dict["content"]
    data     = note_dict["data"]
    creator  = note_dict["creator"]
    priority = note_dict["priority"]
    mtime    = note_dict["mtime"]

    if xconfig.DB_ENGINE == "sqlite":
        db         = xtables.get_file_table()
        id         = db.insert(**note_dict)
        update_note_content(id, content, data)
        return id
    else:
        id = dbutil.timeseq()
        key = "note_full:%s" % id
        note_dict["id"] = id
        dbutil.put(key, note_dict)
        score = "%02d:%s" % (priority, mtime)
        dbutil.zadd("z:note.recent:%s" % creator, score, id)
        return id

def rdb_update_note(where, **kw):
    db      = xtables.get_file_table()
    note_id = where.get('id')
    content = kw.get('content')
    data    = kw.get('data')

    kw["mtime"] = dateutil.format_time()
    kw["atime"] = dateutil.format_time()
    # 处理乐观锁
    version = where.get("version")
    if version != None:
        kw["version"] = version + 1
    # 这两个字段废弃，移动到单独的表中
    if 'content' in kw:
        del kw['content']
        kw['content'] = ''
    if 'data' in kw:
        del kw['data']
        kw['data'] = ''
    rows = db.update(where = where, vars=None, **kw)
    if rows > 0:
        # 更新成功后再更新内容，不考虑极端的冲突情况
        update_note_content(note_id, content, data)
    return rows

def kv_put_note(note_id, note):
    priority = note.priority
    mtime    = note.mtime
    creator  = note.creator
    dbutil.put("note_full:%s" % note_id, note)

    score = "%02d:%s" % (priority, mtime)
    if note.is_deleted:
        dbutil.zrem("z:note.recent:%s" % creator, note_id)
    else:
        dbutil.zadd("z:note.recent:%s" % creator, score, note_id)

    del note['content']
    del note['data']
    dbutil.put("note_tiny:%s" % note_id, note)

def kv_update_note(where, **kw):
    note_id   = where['id']
    creator   = where.get('creator')
    content   = kw.get('content')
    data      = kw.get('data')
    priority  = kw.get('priority')
    name      = kw.get("name")
    atime     = kw.get("atime")
    parent_id = kw.get("parent_id")

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
        if parent_id:
            note.parent_id = parent_id
        note.mtime   = xutils.format_time()
        note.version += 1
        
        # 只修改优先级
        if len(kw) == 1 and kw.get('priority') != None:
            note.version -= 1
        # 只修改名称
        if len(kw) == 1 and kw.get('name') != None:
            note.version -= 1

        # TODO 处理移动分类的情况
        kv_put_note(note_id, note)
        return 1
    return 0


def update_note(where, **kw):
    if xconfig.DB_ENGINE == "sqlite":
        return rdb_update_note(where, **kw)
    else:
        return kv_update_note(where, **kw)

def rdb_get_by_name(name):
    db = get_file_db()
    result = get_db().select_first(where=dict(name=name, is_deleted=0))
    if result is None:
        return None
    return build_note(result)

def kv_get_by_name(name):
    def find_func(key, value):
        return value.name == name
    result = dbutil.prefix_list("note:", find_func, 0, 1)
    if len(result) > 0:
        return result[0]
    return None

def get_by_name(name):
    if xconfig.DB_ENGINE == "sqlite":
        return rdb_get_by_name(name)
    else:
        return kv_get_by_name(name)

def visit_note(id):
    if xconfig.DB_ENGINE == "sqlite":
        db = xtables.get_file_table()
        sql = "UPDATE file SET visited_cnt = visited_cnt + 1, atime=$atime where id = $id"
        db.query(sql, vars = dict(atime = xutils.format_datetime(), id=id))
    else:
        note = get_by_id(id)
        if note:
            note.atime = xutils.format_datetime()
            if note.visited_cnt is None:
                note.visited_cnt = 0
            note.visited_cnt += 1
            kv_put_note(id, note)

def delete_note(id):
    if xconfig.DB_ENGINE == "sqlite":
        db = xtables.get_file_table()
        sql = "UPDATE file SET is_deleted = 1, mtime=$mtime where id = $id"
        db.query(sql, vars = dict(mtime = xutils.format_datetime(), id=id))
    else:
        note = get_by_id(id)
        if note:
            note.mtime = xutils.format_datetime()
            note.is_deleted = 1
            kv_put_note(id, note)

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

def update(where, **kw):
    db = get_file_db()
    kw["mtime"] = dateutil.format_time()
    # 处理乐观锁
    version = where.get("version")
    if version:
        kw["version"] = version + 1
    return db.update(where = where, vars=None, **kw)

def update_children_count(parent_id, db=None):
    if parent_id is None or parent_id == "":
        return
    if db is None:
        db = get_file_db()
    group_count = db.count(where="parent_id=$parent_id AND is_deleted=0", vars=dict(parent_id=parent_id))
    db.update(size=group_count, where=dict(id=parent_id))

def delete_by_id(id):
    update(where=dict(id=id), is_deleted=1)

def insert(file):
    name = file.name
    f = get_by_name(name)
    if f is not None:
        raise FileExistsError(name)
    if not hasattr(file, "is_deleted"):
        file.is_deleted = 0
    return get_db().insert(**file)
        
def get_db():
    return get_file_db()


def build_sql_row(obj, k):
    v = getattr(obj, k)
    if v is None: return 'NULL'
    return to_sqlite_obj(v)

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

@xutils.timeit(name = "NoteDao.ListGroup:sqlite", logfile = True)
def rdb_list_group(current_name = None):
    if current_name is None:
        current_name = str(xauth.get_current_name())
    cache_key = "[%s]note.group.list" % current_name
    value = cacheutil.get(cache_key)
    if value is None:
        sql = "SELECT * FROM file WHERE creator = $creator AND type = 'group' AND is_deleted = 0 ORDER BY name LIMIT 1000"
        value = list(xtables.get_file_table().query(sql, vars = dict(creator=current_name)))
        cacheutil.set(cache_key, value, expire=600)
    return value

@xutils.timeit(name = "NoteDao.ListGroup:leveldb", logfile = True)
def kv_list_group(creator = None):
    # TODO 添加索引优化
    def list_group_func(key, value):
        return value.type == "group" and value.creator == creator and value.is_deleted == 0

    notes = dbutil.prefix_list("note_tiny:", list_group_func)
    notes.sort(key = lambda x: x.name)
    return notes

def list_group(current_name = None):
    if current_name is None:
        current_name = str(xauth.get_current_name())

    if xconfig.DB_ENGINE == "sqlite":
        return rdb_list_group(current_name)
    else:
        return kv_list_group(current_name)

def rdb_list_note(creator, parent_id, offset, limit):
    db = xtables.get_note_table()
    where_sql = "parent_id=$parent_id AND is_deleted=0 AND (creator=$creator OR is_public=1)"
    files = db.select(where = where_sql, 
        vars = dict(parent_id=parent_id, is_deleted=0, creator=creator), 
        order = "name", 
        limit = limit, 
        offset = offset)
    return files

@xutils.timeit(name = "NoteDao.ListNote:leveldb", logfile = True, logargs=True)
def kv_list_note(creator, parent_id, offset, limit):
    # TODO 添加索引优化
    def list_note_func(key, value):
        if value.is_deleted:
            return False
        if value.type == "group":
            return False
        return (value.is_public or value.creator == creator) and value.parent_id == parent_id

    notes = dbutil.prefix_list("note_tiny:", list_note_func, offset, limit)
    notes.sort(key = lambda x: x.name)
    return notes

def list_note(*args):
    if xconfig.DB_ENGINE == "sqlite":
        return rdb_list_note(*args)
    else:
        return kv_list_note(*args)

@xutils.timeit(name = "NoteDao.ListRecentCreated", logfile = True)
def list_recent_created(parent_id = None, offset = 0, limit = 10):
    where = "is_deleted = 0 AND (creator = $creator)"
    if parent_id != None:
        where += " AND parent_id = %s" % parent_id
    db = xtables.get_file_table()
    result = list(db.select(where = where, 
            vars   = dict(creator = xauth.get_current_name()),
            order  = "ctime DESC",
            offset = offset,
            limit  = limit))
    fill_parent_name(result)
    return result

@xutils.timeit(name = "NoteDao.ListRecentViewed", logfile = True, logargs = True)
def list_recent_viewed(creator = None, offset = 0, limit = 10):
    where = "is_deleted = 0 AND (creator = $creator)"
    db = xtables.get_file_table()
    result = list(db.select(where = where, 
            vars   = dict(creator = creator),
            order  = "atime DESC",
            offset = offset,
            limit  = limit))
    fill_parent_name(result)
    return result

@xutils.timeit(name = "NoteDao.ListRecentEdit:sqlite", logfile = True, logargs = True)
def rdb_list_recent_edit(parent_id=None, offset=0, limit=None):
    if limit is None:
        limit = xconfig.PAGE_SIZE
    db = xtables.get_file_table()
    creator = xauth.get_current_name()
    if creator:
        where = "is_deleted = 0 AND (creator = $creator) AND type != 'group'"
    else:
        # 未登录
        where = "is_deleted = 0 AND is_public = 1 AND type != 'group'"
    
    cache_key = "[%s]note.recent$%s$%s" % (creator, offset, limit)
    files = cacheutil.get(cache_key)
    if files is None:
        files = list(db.select(what="name, id, parent_id, ctime, mtime, type, creator, priority", 
            where = where, 
            vars   = dict(creator = creator),
            order  = "priority DESC, mtime DESC",
            offset = offset,
            limit  = limit))
        fill_parent_name(files)
        cacheutil.set(cache_key, files, expire=600)
    return files

@xutils.timeit(name = "NoteDao.ListRecentEdit:leveldb", logfile = True, logargs = True)
def list_recent_edit(parent_id = None, offset=0, limit=None):
    """通过KV存储实现"""

    if xconfig.DB_ENGINE == "sqlite":
        return rdb_list_recent_edit(parent_id, offset, limit)

    if limit is None:
        limit = xconfig.PAGE_SIZE

    user = xauth.get_current_name()
    if user is None:
        user = "public"
    
    id_list   = dbutil.zrange("z:note.recent:%s" % user, -offset-1, -offset-limit)
    note_dict = batch_query(id_list)
    files     = []

    for id in id_list:
        note = note_dict.get(id)
        if note:
            files.append(note)
    fill_parent_name(files)
    return files

def list_by_date(field, creator, date):
    db = xtables.get_file_table()
    date_pattern = date + "%"

    if field == "name":
        where = "creator = $creator AND is_deleted = 0 AND name LIKE $date"
        date_pattern = "%" + date + "%"
    elif field == "mtime":
        where = "creator = $creator AND is_deleted = 0 AND mtime LIKE $date"
    else:
        where = "creator = $creator AND is_deleted = 0 AND ctime LIKE $date"
    files = list(db.select(what="name, id, parent_id, ctime, mtime, type, creator", 
            where = where, 
            vars   = dict(creator = creator, date = date_pattern),
            order  = "name DESC"))
    fill_parent_name(files)

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
        count = dbutil.prefix_count("note_full", count_func)
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
            return (value.is_public or value.creator == creator) and value.parent_id == parent_id

        return dbutil.prefix_count("note_tiny", list_note_func)

def list_tag(user_name):
    t = Timer()
    t.start()
    cache_key = "%s@tag_list" % user_name
    tag_list = xutils.cache_get(cache_key)
    if tag_list is None:
        db = xtables.get_file_tag_table()
        sql = """SELECT LOWER(name) AS name, COUNT(*) AS amount FROM file_tag 
            WHERE (user=$user OR is_public=1) 
            GROUP BY LOWER(name) ORDER BY amount DESC, name ASC""";
        tag_list = list(db.query(sql, vars = dict(user = user_name)))
        xutils.cache_put(cache_key, tag_list, 60 * 10)
    t.stop()
    xutils.trace("NoteDao.ListTag", "", t.cost_millis())
    return tag_list

@xutils.timeit(name = "NoteDao.FindPrev", logfile = True)
def find_prev_note(note):
    where = "parent_id = $parent_id AND name < $name ORDER BY name DESC LIMIT 1"
    table = xtables.get_file_table()
    return table.select_first(where = where, vars = dict(name = note.name, parent_id = note.parent_id))

@xutils.timeit(name = "NoteDao.FindNext", logfile = True)
def find_next_note(note):
    where = "parent_id = $parent_id AND name > $name ORDER BY name ASC LIMIT 1"
    table = xtables.get_file_table()
    return table.select_first(where = where, vars = dict(name = note.name, parent_id = note.parent_id))

def update_priority(creator, id, value):
    table = xtables.get_file_table()
    rows = table.update(priority = value, where = dict(creator = creator, id = id))
    cache_key = "[%s]note.recent" % creator
    cacheutil.prefix_del(cache_key)
    return rows > 0

def add_history(id, version, note):
    # print("add_history", id, version, note)
    # table   = xtables.get_note_history_table()
    # table.insert(name = name, note_id = id, content = content, version = version, mtime = mtime)
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

def rdb_search_name(words, groups=None):
    if not isinstance(words, list):
        words = [words]
    like_list = []
    vars = dict()
    for word in words:
        like_list.append('name LIKE %s ' % to_sqlite_obj('%' + word.upper() + '%'))
    sql = "SELECT name, id, parent_id, ctime, mtime, type, creator FROM file WHERE %s AND is_deleted == 0" % (" AND ".join(like_list))
    sql += " AND (is_public = 1 OR creator = $creator)"
    sql += " ORDER BY mtime DESC LIMIT 1000";
    vars["creator"] = groups
    all = xtables.get_file_table().query(sql, vars=vars)
    return [file_wrapper(item) for item in all]

def kv_search_name(words, creator=None):
    words = [word.lower() for word in words]
    def search_func(key, value):
        if value.is_deleted:
            return False
        return (value.creator == creator or value.is_public) and textutil.contains_all(value.name.lower(), words)
    result = dbutil.prefix_list("note_tiny", search_func, 0, -1)
    return [file_wrapper(item) for item in result]

def search_name(words, creator=None):
    if xconfig.DB_ENGINE == "sqlite":
        return rdb_search_name(words, creator)
    else:
        return kv_search_name(words, creator)

def rdb_search_content(words, groups=None):
    """full search the files
    """
    if not isinstance(words, list):
        words = [words]
    content_like_list = []
    vars = dict()
    for word in words:
        content_like_list.append('note_content.content like %s' % to_sqlite_obj('%' + word.upper() + '%'))
    sql = "SELECT file.id AS id, file.parent_id AS parent_id, file.name AS name, file.ctime AS ctime, file.mtime AS mtime, file.type AS type, file.creator AS creator FROM file JOIN note_content ON file.id = note_content.id WHERE file.is_deleted == 0 AND "
    sql += " AND ".join(content_like_list)
    if groups != "admin":
        sql += " AND (file.is_public = 1 OR file.creator = $creator)"
    sql += " order by mtime desc limit 1000"

    vars["creator"] = groups
    all = xtables.get_file_table().query(sql, vars=vars)
    return [file_wrapper(item) for item in all]

def kv_search_content(words, creator=None):
    words = [word.lower() for word in words]
    def search_func(key, value):
        if value.content is None:
            return False
        return (value.creator == creator or value.is_public) and textutil.contains_all(value.content.lower(), words)
    result = dbutil.prefix_list("note_full", search_func, 0, -1)
    return [file_wrapper(item) for item in result]

def search_content(words, creator=None):
    if xconfig.DB_ENGINE == "sqlite":
        return rdb_search_content(words, creator)
    else:
        return kv_search_content(words, creator)

xutils.register_func("note.create", create_note)
xutils.register_func("note.update", update_note)
xutils.register_func("note.visit",  visit_note)
xutils.register_func("note.count",  count_note)
xutils.register_func("note.delete", delete_note)
xutils.register_func("note.get_by_id", get_by_id)
xutils.register_func("note.get_by_name", get_by_name)
xutils.register_func("note.search_name", search_name)
xutils.register_func("note.search_content", search_content)
xutils.register_func("note.list_path", list_path)
xutils.register_func("note.list_group", list_group)
xutils.register_func("note.list_note", list_note)
xutils.register_func("note.list_tag", list_tag)
xutils.register_func("note.list_recent_created", list_recent_created)
xutils.register_func("note.list_recent_edit", list_recent_edit)
xutils.register_func("note.list_recent_viewed", list_recent_viewed)
xutils.register_func("note.list_by_date", list_by_date)
xutils.register_func("note.count_recent_edit", count_user_note)
xutils.register_func("note.count_user_note", count_user_note)
xutils.register_func("note.count_ungrouped", count_ungrouped)
xutils.register_func("note.get_by_id_creator", get_by_id_creator)
xutils.register_func("note.find_prev_note", find_prev_note)
xutils.register_func("note.find_next_note", find_next_note)
xutils.register_func("note.update_priority", update_priority)
xutils.register_func("note.add_history", add_history)
xutils.register_func("note.list_history", list_history)
xutils.register_func("note.get_history", get_history)

