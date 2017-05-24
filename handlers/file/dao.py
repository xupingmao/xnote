# encoding=utf-8
# Created by xupingmao on 2017/04/16

"""资料的DAO操作集合

由于sqlite是单线程，所以直接使用方法操作
如果是MySQL等数据库，使用 threadeddict 来操作，直接用webpy的ctx
"""
import re
import sqlite3

import web.db as db
from util import dateutil
import config

MAX_VISITED_CNT = 200

from xutils import readfile, savetofile
readFile = readfile
writeFile = savetofile

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
            
    def fromDict(dict, option=None):
        """build fileDO from dict"""
        name = dict['name']
        file = FileDO(name)
        for key in dict:
            file[key] = dict[key]
            # setattr(file, key, dict[key])
        if hasattr(file, "content") and file.content is None:
            file.content = ""
        if option:
            file.option = option
        if file.type == "post":
            file.url = "/file/post?id={}".format(dict["id"])
        else:
            file.url = "/file/edit?id={}".format(dict["id"])
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
    if not (isinstance(text, str)):
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


def get_category(limit = None):
    db = get_db()
    if limit is None:
        sql = "select * from file where is_deleted != 1 and parent_id = 0 and related not like '%%hide%%' order by sctime desc"
    else:
        sql = "select * from file where is_deleted != 1 and parent_id = 0 and related not like '%%hide%%' order by name desc limit %s" % limit
    all = db.execute(sql)
    return [FileDO.fromDict(item) for item in all]

def get_children_by_id(id):
    db = get_db()
    all = db.execute("select * from file where is_deleted != 1 and parent_id = %s order by sctime desc" % id)
    return [FileDO.fromDict(item) for item in all]

def get_by_id(id, db=None):
    sql = "select * from file where id = %s" % id
    if db is None:
        db = FileDB();
    result = db.execute(sql)
    if len(result) is 0:
        return None
    return FileDO.fromDict(result[0])

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

def search_name(words, limit=None):
    if not isinstance(words, list):
        words = [words]
    like_list = []
    for word in words:
        like_list.append('name like %s ' % repr('%' + word.upper() + '%'))
    sql = "select * from file where %s and is_deleted != 1 order by satime desc limit 1000" % (" AND ".join(like_list))
    if limit:
        sql += " limit {}".format(limit)
    db = FileDB()
    all = db.execute(sql)
    return [FileDO.fromDict(item) for item in all]

def visit_by_id(id):
    sql = "update file set visited_cnt = visited_cnt + 1, satime='%s' where id = %s and visited_cnt < %s" % \
        (dateutil.format_time(), id, MAX_VISITED_CNT)
    return get_db().execute(sql)

def get_recent_visit(count):
    db = FileDB()
    all = db.execute("select * from file where is_deleted != 1 and not (related like '%%HIDE%%') order by satime desc limit %s" % count)
    return [FileDO.fromDict(item) for item in all]

def get_recent_created(count):
    db = FileDB()
    all = db.execute("SELECT * FROM file WHERE is_deleted != 1 ORDER BY sctime DESC LIMIT %s" % count)
    return [FileDO.fromDict(item) for item in all]

def get_recent_modified(count):
    db = FileDB()
    all = db.execute("SELECT * FROM file WHERE is_deleted != 1 ORDER BY smtime DESC LIMIT %s" % count)
    return [FileDO.fromDict(item) for item in all]

def update(where, **kw):
    db = get_file_db()
    kw["smtime"] = dateutil.format_time()
    # 处理乐观锁
    version = where.get("version")
    if version:
        kw["version"] = version + 1
    return db.update("file", where, vars=None, **kw)

def delete_by_id(id):
    update(where=dict(id=id), is_deleted=1)

def get_by_name(name):
    sql = "select * from file where name = %s and is_deleted != 1" % to_sqlite_obj(name)
    result = get_db().execute(sql)
    if len(result) is 0:
        return None
    return FileDO.fromDict(result[0])

def insert(file):
    name = file.name
    f = get_by_name(name)
    if f is not None:
        raise FileExistsError(name)
    if not hasattr(file, "is_deleted"):
        file.is_deleted = 0
    if not hasattr(file, "ctime"):
        file.ctime = dateutil.get_seconds()
        file.sctime = dateutil.format_time(file.ctime)
    if not hasattr(file, "atime"):
        file.atime = dateutil.get_seconds()
        file.satime = dateutil.format_time(file.atime)
    if not hasattr(file, "mtime"):
        file.mtime = dateutil.get_seconds()
        file.smtime = dateutil.format_time(file.mtime)

    if hasattr(file, "atime"):
        delattr(file, "atime")
    if hasattr(file, "ctime"):
        delattr(file, "ctime")
    if hasattr(file, "mtime"):
        delattr(file, "mtime")

    values = [build_sql_row(file, k) for k in file]
    sql = "insert into file (%s) values (%s)" % (','.join(file), ",".join(values))
    # print(sql)
    return get_db().execute(sql)
        

def get_db():
    return FileDB()

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

