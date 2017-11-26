# encoding=utf-8
# Created by xupingmao on 2017/04/16

"""资料的DAO操作集合

由于sqlite是单线程，所以直接使用方法操作
如果是MySQL等数据库，使用 threadeddict 来操作，直接用webpy的ctx
"""
import re
import six
import web.db as db
import xconfig
import xtables
import xutils

from xutils import readfile, savetofile
from util import dateutil

sqlite3 = xutils.sqlite3
MAX_VISITED_CNT = 200

readFile = readfile

config  = xconfig
DB_PATH = config.DB_PATH


class FileDO(dict):
    """This class behaves like both object and dict"""
    def __init__(self, name):
        self.id = None
        self.related = ''
        if isinstance(name, list) or isinstance(name, tuple):
            self.name = name[0]
            self.addRelatedNames(name)
        else:
            self.name = name
            self.addRelatedName(name)
        # self.path = getRandomPath()
        self.size = 0
        t = dateutil.get_seconds()
        self.mtime = t
        self.atime = t
        self.ctime = t
        # self.status = 0
        self.visited_cnt = 0

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
    
    def addRelatedName(self, name):
        if name is None:
            return
        name = name.upper()
        if self.related == '':
            self.related = ',%s,' % name
            return
        if name == '':
            return
        tag = ',%s,' % name
        if tag in self.related:
            return
        self.related += name + ','
        
    def delRelatedName(self, name):
        name = name.upper()
        if name == self.name.upper():
            raise FileRelationOptionError("can not remove itself from related!!!")
        names = self.related.split(',')
        names.remove(name)
        self.related = ','.join(names)
        
    def addRelatedNames(self, names):
        for name in names:
            self.addRelatedName(name)
            
    def fixRelated(self):
        ''' this is a deprecated function '''
        related = self.related
        self.related = related.upper()
        name = self.name.upper()
        if name not in self.related:
            self.addRelatedName(name)
        if self.related[0] != ',':
            self.related = ',' + self.related
        if self.related[-1] != ',':
            self.related += ','
        if related != self.related:
            self.save()
            
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
        file.url = "/file/view?id={}".format(dict["id"])
        return file
        
    def setBase(self, base):
        self.base = base
        
    def get_content(self):
        if self.content is None:
            self.content = ""
        if "CODE-" in self.related and not self.content.startswith("```"):
            m = re.match(r".*CODE-([A-Z]*)", self.related)
            codename = ""
            if m:
                codename = m.groups()[0]
            return "```%s\n%s\n```" % (codename, self.content)
        return self.content
        
    def writeContent(self, content):
        raise Exception("not implemented")

def getMilliSecond():
    t = time.time()
    ms = t - int(t)
    return '%03d' % int(ms*1000)
    
def getRandomPath():
    return time.strftime("%Y/%m/%d-%H%M%S")+"-"+getMilliSecond()

def to_sqlite_obj(text):
    if text is None:
        return "NULL"
    if not isinstance(text, six.string_types):
        return repr(text)
    # text = text.replace('\\', '\\')
    text = text.replace("'", "''")
    return "'" + text + "'"
    


class FileRelationOptionError(Exception):
    def __init__(self, msg):
        self.error = msg
        
    def __str__(self):
        return str(self.error)

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
    return db.SqliteDB(db=config.DB_PATH)

def get_pathlist(db, file):
    pathlist = []
    # TODO LIMIT
    while file is not None:
        file.url = "/file/view?id=%s" % file.id
        pathlist.insert(0, file)
        if file.parent_id == 0:
            break
        else:
            file = db.select_one(where=dict(id=file.parent_id))
    return pathlist

def get_category(name = None, limit = None):
    db = get_db()
    vars = dict()

    if limit is None:
        limit = 200
    sql = "SELECT * FROM file WHERE is_deleted != 1 AND parent_id = 0 AND type = 'group'"
    if name is not None:
        sql += " AND creator = $creator"
        vars["creator"] = name
    sql += " ORDER BY priority DESC, ctime DESC LIMIT $limit"
    vars["limit"] = limit
    all = db.query(sql, vars=vars)
    return [FileDO.fromDict(item) for item in all]

def get_children_by_id(id):
    db = get_db()
    all = db.execute("SELECT * from file where parent_id = %s AND is_deleted != 1 order by ctime desc" % id)
    return [FileDO.fromDict(item) for item in all]

def get_by_id(id, db=None):
    if db is None:
        db = get_db()
    first = db.select_one(where=dict(id=id))
    if first is not None:
        return FileDO.fromDict(first)
    return None

def get_by_name(name):
    result = get_db().select_one(where=dict(name=name, is_deleted=0))
    if result is None:
        return None
    return FileDO.fromDict(result)

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

def search_name(words, limit=None, file_type=None):
    if not isinstance(words, list):
        words = [words]
    like_list = []
    for word in words:
        like_list.append('name like %s ' % repr('%' + word.upper() + '%'))
    sql = "SELECT * from file WHERE %s and is_deleted != 1 " % (" AND ".join(like_list))
    if file_type != None:
        sql += " AND type = %r" % file_type
    sql += " ORDER BY atime DESC"
    if not limit:
        limit = 200
    sql += " LIMIT {}".format(limit)
    db = FileDB()
    all = db.execute(sql)
    return [FileDO.fromDict(item) for item in all]

def visit_by_id(id):
    db = get_db()
    sql = "UPDATE file SET visited_cnt = visited_cnt + 1, atime='%s' where id = %s and visited_cnt < %s" % \
        (dateutil.format_time(), id, MAX_VISITED_CNT)
    return db.query(sql)

def get_recent_visit(count):
    db = FileDB()
    all = db.execute("select * from file where is_deleted != 1 and not (related like '%%HIDE%%') order by atime desc limit %s" % count)
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
    return db.update("file", where, vars=None, **kw)

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
    return xtables.get_file_table()

class FileDB:

    def __init__(self, dbpath = None):
        if dbpath is None:
            dbpath = config.DB_PATH
        self.path = dbpath
        self.conn = sqlite3.connect(dbpath)
        self.cursor = self.conn.cursor()

    def setup():
        ''' setup database file '''
        filedb = FileDB()
            
    def __del__(self):
        self.conn.close()
        
    def execute0(self, sql):
        cursorobj = self.cursor
        try:
            cursorobj.execute(sql)
            result = cursorobj.fetchall()
            self.conn.commit()
            return result
        except Exception:
            raise
        return result
        
    def execute(self, sql):
        cursorobj = self.cursor
        try:
            if sql.startswith("update") and "where" not in sql:
                raise Exception("update without where!!!")
            cursorobj.execute(sql)
            result = cursorobj.fetchall()
            result1 = []
            for single in result:
                resultMap = {}
                for i, desc in enumerate(cursorobj.description):
                    name = desc[0]
                    resultMap[name] = single[i]
                result1.append(resultMap)
            self.conn.commit()
            return result1
        except Exception as e:
            raise e
        return result

def getWords(line):
    line = line.strip()
    words = line.split(' ')
    new_words = []
    for word in words:
        if word != '' : new_words.append(word)
    return new_words

    
def printFile(file):
    if isinstance(file, list):
        for single in file:
            printFile(single)
        return
    print('name=%s, related=%s, visited_cnt=%s' % (file.name, file.related, file.visited_cnt))
    

def static_search(context, words):
    """search file, sqlite do not support call between different threads"""
    return FileService().smart_search(context, words)

def full_search(words):
    """ full search the files """
    if not isinstance(words, list):
        words = [words]
    content_like_list = []
    # name_like_list = []
    for word in words:
        content_like_list.append('content like %s ' % repr('%' + word.upper() + '%'))
    # for word in words:
    #     name_like_list.append("related like %s " % repr("%" + word.upper() + '%'))
    sql = "select * from file where (%s) and is_deleted != 1 limit 1000" \
        % " AND ".join(content_like_list)
    all = FileDB().execute(sql)
    return [FileDO.fromDict(item) for item in all]
    # context["files"] = [FileDO.fromDict(item) for item in all]

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

