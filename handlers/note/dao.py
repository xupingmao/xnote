# encoding=utf-8
# Created by xupingmao on 2017/04/16
# @modified 2019/04/25 22:09:42

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
from xutils import readfile, savetofile, sqlite3
from xutils import dateutil, cacheutil, Timer

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

def batch_query(id_list):
    db = xtables.get_note_table()
    result = db.select(where = "id IN $id_list", vars = dict(id_list = id_list))
    dict_result = dict()
    for item in result:
        dict_result[item.id] = item
    return dict_result

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

def get_pathlist(db, file, limit = 2):
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

def get_by_id(id, db=None):
    if db is None:
        db = get_file_db()
    first = db.select_first(where=dict(id=id))
    if first is not None:
        return build_note(first)
    return None

def get_by_id_creator(id, creator, db=None):
    if db is None:
        db = get_file_db()
    first = db.select_first(where=dict(id=id, creator = creator))
    if first is not None:
        return build_note(first)
    return None

def get_by_name(name, db=None):
    if db is None:
        db = get_file_db()
    result = get_db().select_first(where=dict(name=name, is_deleted=0))
    if result is None:
        return None
    return build_note(result)

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

def visit_by_id(id, db = None):
    sql = "UPDATE file SET visited_cnt = visited_cnt + 1, atime='%s' where id = %s " % \
        (dateutil.format_time(), id)
    return db.query(sql)

def get_recent_visit(count):
    db = FileDB()
    all = db.execute("SELECT * from file where is_deleted != 1 and not (related like '%%HIDE%%') order by atime desc limit %s" % count)
    return [FileDO.fromDict(item) for item in all]

def get_recent_created(count):
    db = FileDB()
    all = db.execute("SELECT * FROM file WHERE is_deleted != 1 ORDER BY ctime DESC LIMIT %s" % count)
    return [FileDO.fromDict(item) for item in all]

def get_recent_modified(count):
    db = FileDB()
    all = db.execute("SELECT * FROM file WHERE is_deleted != 1 ORDER BY mtime DESC LIMIT %s" % count)
    return [FileDO.fromDict(item) for item in all]

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

def list_group(current_name = None):
    if current_name is None:
        current_name = str(xauth.get_current_name())
    t1 = time.time()
    cache_key = "[%s]note.group.list" % current_name
    value = cacheutil.get(cache_key)
    if value is None:
        sql = "SELECT * FROM file WHERE creator = $creator AND type = 'group' AND is_deleted = 0 ORDER BY name LIMIT 1000"
        value = list(xtables.get_file_table().query(sql, vars = dict(creator=current_name)))
        cacheutil.set(cache_key, value, expire=600)
    t2 = time.time()
    xutils.trace("NoteDao.ListGroup", "", int((t2-t1)*1000))
    return value

def list_recent_created(parent_id = None, offset = 0, limit = 10):
    t = Timer()
    t.start()
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
    t.stop()
    xutils.trace("NoteDao.ListRecentCreated", "", t.cost_millis())
    return result

def list_recent_viewed(creator = None, offset = 0, limit = 10):
    t = Timer()
    t.start()
    where = "is_deleted = 0 AND (creator = $creator)"
    db = xtables.get_file_table()
    result = list(db.select(where = where, 
            vars   = dict(creator = creator),
            order  = "atime DESC",
            offset = offset,
            limit  = limit))
    fill_parent_name(result)
    t.stop()
    xutils.trace("NoteDao.ListRecentViewed", "", t.cost_millis())
    return result

def list_recent_edit(parent_id=None, offset=0, limit=None):
    if limit is None:
        limit = xconfig.PAGE_SIZE
    db = xtables.get_file_table()
    t = Timer()
    t.start()
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
    t.stop()
    xutils.trace("NoteDao.ListRecentEdit", "", t.cost_millis())
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

def count_user_note(creator):
    t = Timer()
    t.start()
    count_key = "[%s]note.count" % creator
    count = cacheutil.get(count_key)
    if count is None:
        db    = xtables.get_file_table()
        where = "is_deleted = 0 AND creator = $creator AND type != 'group'"
        count = db.count(where, vars = dict(creator = xauth.get_current_name()))
        cacheutil.set(count_key, count, expire=600)
    t.stop()
    xutils.trace("NoteDao.CountRecentEdit", "", t.cost_millis())
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

def find_prev_note(note):
    where = "parent_id = $parent_id AND name < $name ORDER BY name DESC LIMIT 1"
    table = xtables.get_file_table()
    return table.select_first(where = where, vars = dict(name = note.name, parent_id = note.parent_id))

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


xutils.register_func("note.list_group", list_group)
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

