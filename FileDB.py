
'''Based on sqlite3
'''


import sqlite3
import os
import time
from io import StringIO
import codecs
import re
import uuid
import time
import config

from util import dateutil
from threading import Thread
# from queue import Queue

def getMilliSecond():
    t = time.time()
    ms = t - int(t)
    return '%03d' % int(ms*1000)
    
def readFile(path):
    fp = open(path, encoding="utf-8")
    content = fp.read()
    fp.close()
    return content
    
def writeFile(path, content):
    fp = open(path, "wb")
    buffer = codecs.encode(content, "utf-8")
    fp.write(buffer)
    fp.close()
    return content
    
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
    
MAX_VISITED_CNT = 200

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

    # def __getitem__(self, key):
    #     return getattr(self, key)

    # def __setitem__(self, key, value):
    #     setattr(self, key, value)
    
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
        
    def save(self):
        if self.id is None:
            FileService.getService().insert(self)
        else:
            FileService.getService().update(self)
            
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

        # abspath = os.path.join(self.base, self.path)
        # if not os.path.isfile(abspath):
        #     return ""
        # return readFile(abspath)
        
    def writeContent(self, content):
        # abspath = os.path.join(self.base, self.path)
        # dirname = os.path.dirname(abspath)
        # basename = os.path.basename(abspath)
        # # print(dirname, abspath, self.base, self.path)
        # if not os.path.exists(dirname):
        #     os.makedirs(dirname)
        # writeFile(abspath, content)
        raise Exception("not implemented")

        
        
class FileExistsError(Exception):
    def __init__(self, name):
        self.error = "file exists!!!name=%s" % repr(name)
        
    def __str__(self):
        return self.error


class FileServiceMethod:

    def __init__(self, thread, method):
        self.thread = thread
        self.method = method

    def __call__(self, *args):
        # print("method %s called, args = %s" % (self.method, args))
        thread = self.thread
        uid = uuid.uuid1().hex
        self.thread.queue.put([uid, self.method, args])

        # print("method put uid = %s" % uid)
        while uid not in self.thread.result:
            time.sleep(0.05)

        ret = self.thread.get_result(uid)
        thread.del_result(uid)
        # print("method call done, result = %s" % ret)
        return ret

class FileServiceThread(Thread):

    def __init__(self):
        Thread.__init__(self)
        self.setDaemon(True)
        self.result = {}
        self.queue = Queue()
        self.service = None


    def __getattr__(self, method):
        return FileServiceMethod(self, method)

    def get_result(self, uid):
        return self.result.get(uid)

    def put_result(self, uid, result):
        self.result[uid] = result

    def del_result(self, uid):
        if uid in self.result:
            del self.result[uid]

    def run(self):
        self.service = FileService()
        while True:
            item = self.queue.get()
            if item is not None:
                uid, method, args = item
                # print("start to call %s" % method)
                result = getattr(self.service, method)(*args)
                # print("put result to %s" % uid)
                self.put_result(uid, result)
            else:
                time.sleep(0.05)



def static_search(context, words):
    """search file, sqlite do not support call between different threads"""
    return FileService().smart_search(context, words)

def full_search(context, words):
    """ full search the files """
    if not isinstance(words, list):
        words = [words]
    like_list = []
    for word in words:
        like_list.append('content like %s ' % repr('%' + word.upper() + '%'))
    sql = "select * from file where %s and is_deleted != 1 limit 1000" % (" AND ".join(like_list))
    all = FileDB().execute(sql)
    context["files"] = [FileDO.fromDict(item) for item in all]
    return all

def build_sql_row(obj, k):
    v = getattr(obj, k)
    if v is None: return 'NULL'
    return to_sqlite_obj(v)

class FileService:
    _db_path = config.get("DB_PATH")

    _inited = False

    def __init__(self, dbpath = None):
        if dbpath is None:
            dbpath = FileService._db_path
        self._db_path = dbpath
        self._db = FileDB(dbpath)
        # self._filter = FileFilter()

    def init(dbpath = None):
        if FileService._inited:
            return

        # service = FileServiceThread()
        # FileService._service = service
        # service.start()
        # print("fileservice thread running")
        # service._filter.init(service.select_all())
        FileService._inited = True

    def instance(dbpath=None):
        # return FileService._service
        return FileService(dbpath)

    def get_path(self):
        return self._db_path
        
    def release(self):
        self._db.close()

    def getTableDefine(self, tableName):
        rs = self._db.execute("pragma table_info('%s')" % tableName)
        result = []
        for item in rs:
            result.append(item)
        return result
            
    def getTableList(self):
        sql = "select name from sqlite_master where type='table' order by name"
        rs = self._db.execute(sql)
        result = []
        for item in rs:
            td = TableDesc(item)
            td.items = getTableDefine(path, td.name)
            result.append(td)
        return result
        
    def insert(self, file):
        name = file.name
        f = self.getByName(name)
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

        values = [build_sql_row(file, k) for k in file]
        sql = "insert into file (%s) values (%s)" % (','.join(file), ",".join(values))
        print(sql)
        # print(sql)
        self._db.execute(sql)
        
    def visitById(self, id):
        sql = "update file set visited_cnt = visited_cnt + 1, satime='%s' where id = %s and visited_cnt < %s" % \
            (dateutil.format_time(), id, MAX_VISITED_CNT)
        self._db.execute(sql)
        
    def update(self, file, *names):
        id = file.id;
        file.mtime = dateutil.get_seconds()
        if file.visited_cnt < MAX_VISITED_CNT:
            file.visited_cnt += 1
        if len(names) > 0:
            keys = names
        else:
            keys = [k for k in file if k != 'id']
        
        values = [ '%s = %s' % (k, build_sql_row(file, k)) for k in keys]
        sql = "update file set %s where id = %s" % (','.join(values), file.id)
        self._db.execute(sql)
        
    def updateField(self, id, key, value):
        sql = "update file set %s = %s where id = %s" % (key, to_sqlite_obj(value), id)
        self._db.execute(sql)
        
    def updateContent(self, id, content):
        sql = "update file set content = %s,size=%s, smtime='%s' where id = %s" \
            % (to_sqlite_obj(content), len(content), dateutil.format_time(), id)
        self._db.execute(sql)

    def getByName(self, name):
        sql = "select * from file where name = %s and is_deleted != 1" % to_sqlite_obj(name)
        result = self._db.execute(sql)
        if len(result) is 0:
            return None
        return FileDO.fromDict(result[0])

    def get_by_name(self, name):
        sql = "select * from file where name = %s and is_deleted != 1" % to_sqlite_obj(name)
        result = self._db.execute(sql)
        if len(result) is 0:
            return None
        return FileDO.fromDict(result[0])
        
    def getById(self, id):
        sql = "select * from file where id = %s" % id
        result = self._db.execute(sql)
        if len(result) is 0:
            return None
        return FileDO.fromDict(result[0])

    def select_by_sql(self, sql):
        sql_lower = sql.lower()
        if "update" in sql_lower:
            raise Exception("update is forbidden")
        if "limit" not in sql_lower:
            raise Exception("require limit")
        return self._db.execute(sql)

    def select_all(self):
        return self._db.execute("select id, name, related, atime, mtime, ctime from file where is_deleted != 1");
        
    def getAll(self, page=0, pagesize=20):
        start = page * pagesize;
        all = self._db.execute('select * from file where is_deleted != 1 limit %s, %s' % (start, pagesize))
        return [FileDO.fromDict(item) for item in all]
        
    def get_top(self, count):
        """Get top visited file"""
        all = self._db.execute("select * from file where is_deleted != 1 order by visited_cnt desc limit %s" % count)
        return [FileDO.fromDict(item) for item in all]

    def get_last(self, count):
        """Get less visited file"""
        all = self._db.execute("select * from file where is_deleted != 1 order by visited_cnt limit %s" % count)
        return [FileDO.fromDict(item) for item in all]
        
    def getRecent(self, count):
        all = self._db.execute("select * from file where is_deleted != 1 and not (related like '%%HIDE%%') order by atime desc limit %s" % count)
        return [FileDO.fromDict(item) for item in all]

    def get_deleted_list(self):
        list = self._db.execute("select * from file where is_deleted = 1 order by mtime desc")
        return [FileDO.fromDict(item, option="physically_delete") for item in list]

    def get_recent_modified(self, days):
        list = self._db.execute("select * from file where smtime > '%s' AND is_deleted != 1 order by smtime desc" 
            % dateutil.before(days=int(days), format=True))
        return [FileDO.fromDict(item) for item in list]

    def get_recent_created(self, days):
        list = self._db.execute("select * from file where ctime > %s order by ctime desc" % dateutil.before(days=int(days)))
        return [FileDO.fromDict(item) for item in list]
        
    def forget(self):
        all = self._db.execute("update file set visited_cnt = visited_cnt - 1 where visited_cnt > 0")
        
    def count(self):
        all = self._db.execute0('select count(1) from file where is_deleted != 1')
        return all[0][0]
        
    def search(self, words):
        if not isinstance(words, list):
            words = [words]
        like_list = []
        for word in words:
            like_list.append('related like %s ' % repr('%' + word.upper() + '%'))
        sql = "select * from file where %s and is_deleted != 1 order by atime desc limit 1000" % (" AND ".join(like_list))
        all = self._db.execute(sql)

        # filter_result = self._filter.search(words)
        # print(filter_result)

        return [FileDO.fromDict(item) for item in all]

    # def filter_search(self, words):
    #     """ search file with filter method """
    #     if not isinstance(words, list):
    #         words = [words]
    #     upper_words = [word.upper() for word in words]
    #     filter_result = self._filter.search(upper_words)
    #     return [FileDO.fromDict(item) for item in filter_result]

    def smart_search(self, result, words):
        ''' search files with rules '''
        result["files"] = self.search(words)
        return 
        
        matched_records = []
        for record in self._records:
            if text_contains(record.full_name, words):
                matched_records.append(record)
        result["matched_records"] = matched_records

        
    def delById(self, id):
        sql = "update file set is_deleted = 1 where id = %s" % id
        self._db.execute(sql)
    
    def delByName(self, name):
        sql = "update file set is_deleted = 1 from file where name = %s" % repr(name)
        self._db.execute(sql)
        
    def delete(self, file):
        if file.id is not None:
            self.delById(file.id)
        else:
            self.delByName(file.name)

    def physically_delete(self, id):
        self._db.execute("delete from file where id=%s" % id)
        
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

def search_name(words):
    if not isinstance(words, list):
        words = [words]
    like_list = []
    for word in words:
        like_list.append('related like %s ' % repr('%' + word.upper() + '%'))
    sql = "select * from file where %s and is_deleted != 1 order by satime desc limit 1000" % (" AND ".join(like_list))
    db = FileDB()
    all = db.execute(sql)
    return [FileDO.fromDict(item) for item in all]

def get_recent_visit(count):
    db = FileDB()
    all = db.execute("select * from file where is_deleted != 1 and not (related like '%%HIDE%%') order by satime desc limit %s" % count)
    return [FileDO.fromDict(item) for item in all]

def update(where = None, **kw):
    db = FileDB()
    values = [ '%s = %s' % (k, to_sqlite_obj(kw[k])) for k in kw]
    sql = "update file set %s where %s" % (','.join(values), where)
    return db.execute(sql)


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
    print(sql)
    # print(sql)
    return get_db().execute(sql)
        

def get_db():
    return FileDB()

class FileDB:

    def createDatabase(self):
        sql = '''create table file (
            id integer primary key autoincrement,
            name text,
            content text,
            path text, -- for local file
            parent_id int default 0, -- for hierarchical filesystem
            children text, -- children
            bin blob, -- for binary data
            size long,
            mtime long, -- seconds
            atime long, -- seconds
            ctime long, -- seconds
            smtime text,
            satime text,
            sctime text,
            related text,
            -- type text default 'text', this is not a requirement, related can do it's work
            visited_cnt int default 0,
            is_deleted int default 0);'''
        self.conn = sqlite3.connect(self.path)
        self.cursor = self.conn.cursor()
        
        sql_config = '''create table xnote_conf (
            id integer primary key autoincrement,
            name text,
            value_start text,
            value_end text,
            is_deleted int default 0
            );'''
        self.execute(sql)
        self.execute(sql_config)


    def __init__(self, dbpath = None):
        if dbpath is None:
            dbpath = config.get("DB_PATH")
        self.path = dbpath
        if not os.path.exists(dbpath):
            self.createDatabase()
        else:
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
    
def repl():
    service = FileService.getService()
    while True:
        line = input('FileDB>')
        words = getWords(line)
        op = words[0]
        try:
            if op == 'q': 
                service.release()
                break
            elif op == 'add' or op == "insert":
                file = FileDO(words[1:])
                file.save()
            elif op == 'search':
                printFile(service.search(words[1:]))
            elif op == "get":
                printFile(service.getByName(words[1]))
            elif op == 'all':
                printFile(service.getAll())
            elif op == "fix":
                file = service.getByName(words[1])
                file.fixRelated()
            elif op == 'delrela':
                file = service.getByName(words[1])
                file.delRelatedName(words[2])
                file.save()
            else:
                print("unknown option %s" % repr(op))
        except Exception as e:
            print(e)
            
if __name__ == "__main__":
    #db = FileDB("test.db")
    #file = FileObj('test')
    # db.insertFileRecord(file)
    #print(db.execute('select * from file'))
    #db.close()
    repl()
        