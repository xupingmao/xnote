# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2020/09/05 11:56:41
# @modified 2020/09/05 11:57:56


class RecordLock:

    _enter_lock = threading.Lock()
    _lock_dict  = dict()

    def __init__(self, lock_key):
        self.lock = None
        self.lock_key = lock_key

    def acquire(self, timeout = -1):
        lock_key = self.lock_key

        wait_time_start = time.time()
        with RecordLock._enter_lock:
            while RecordLock._lock_dict.get(lock_key) != None:
                # 如果复用lock，可能导致无法释放锁资源
                time.sleep(0.001)
                if timeout > 0:
                    wait_time = time.time() - wait_time_start
                    if wait_time > timeout:
                        return False
            # 由于_enter_lock已经加锁了，_lock_dict里面不需要再使用锁
            RecordLock._lock_dict[lock_key] = True
        return True

    def release(self):
        del RecordLock._lock_dict[self.lock_key]

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, type, value, traceback):
        self.release()

    def __del__(self):
        self.release()

def search_escape(text):
    if not (isinstance(text, str) or isinstance(text, unicode)):
        return text
    text = text.replace('/', '//')
    text = text.replace("'", '\'\'')
    text = text.replace('[', '/[')
    text = text.replace(']', '/]')
    #text = text.replace('%', '/%')
    #text = text.replace('&', '/&')
    #text = text.replace('_', '/_')
    text = text.replace('(', '/(')
    text = text.replace(')', '/)')
    return "'%" + text + "%'"

def to_sqlite_obj(text):
    if text is None:
        return "NULL"
    if not (isinstance(text, str)):
        return repr(text)
    # text = text.replace('\\', '\\')
    text = text.replace("'", "''")
    return "'" + text + "'"
    
def escape(text):
    if not (isinstance(text, str)):
        return text
    #text = text.replace('\\', '\\\\')
    text = text.replace("'", "''")
    return "'" + text + "'"

class DatabaseModifer:

    def __init__(self, path):
        self.conn = sqlite3.connect(path)

    def add_column(self, name, type, default):
        sql = "create table from "

def execute(path, sql):
    db = sqlite3.connect(path)
    cursorobj = db.cursor()
    try:
        cursorobj.execute(sql)
        result = cursorobj.fetchall()
        db.commit()
    except Exception:
        raise
    db.close()
    return result

def execute(path, sql):
    db = sqlite3.connect(path)
    cursorobj = db.cursor()
    try:
        cursorobj.execute(sql)
        kv_result = []
        result = cursorobj.fetchall()
        for single in result:
            resultMap = {}
            for i, desc in enumerate(cursorobj.description):
                name = desc[0]
                resultMap[name] = single[i]
            kv_result.append(resultMap)
        db.commit()
        return kv_result
    except Exception:
        raise
    finally:
        db.close()
    
def get_update_sql(table, update_dict, condition_dict):
    """
    >>> from collections import OrderedDict;get_update_sql('test', OrderedDict(name='hello', age=10), dict(id=10))
    "update test set name='hello',age=10 where id=10"
    """
    update_str = "," .join(["%s=%s" % (name, to_sqlite_obj(update_dict[name])) for name in update_dict])
    condition_str = ",".join(["%s=%s" % (name, to_sqlite_obj(condition_dict[name])) for name in condition_dict])
    sql = "update %s set %s where %s" % (table, update_str, condition_str)
    return sql

def update(path, table, update_dict, condition_dict):
    sql = get_update_sql(table, update_dict, condition_dict)
    print(sql)
    return execute(path, sql)

def select(path, table, **kw):
    where_sql = ",".join(["%s=%s" % (name, to_sqlite_obj(kw[name])) for name in kw])
    sql = "select * from %s where %s" % (table, where_sql)
    return execute(path, sql)

class ObjDB:
    '''
    @staticmethod
    def getInstance():
        if not instance:
            instance = ObjDB()
        return instance'''
    
    def __init__(self, path):
        self.connect(path)
        
    def connect(self, path):
        dirname = util.utf8(os.path.dirname(__file__))
        self.path = os.path.join(dirname, path)
    
    def reconnect(self):
        # logger.info("connect %s" % self.path)
        self.db = sqlite3.connect(self.path)
        return self.db
    
    def done(self):
        self.db.close()
        
    def get_tables(self):
        return self.select("sqlite_master", "*")
        
    def get_table_desc(self, name):
        rs = self.execute("pragma table_info('%s')" % name)
        return rs
    
    def close(self):
        self.db.close()
        
    def select(self, table, names, where = None):
        db = self.reconnect()
        if names == '*':
            names_str = '*'
        else:
            names_str = ','.join(names)
        if where:
            where = "where %s" % where
        else:
            where = ""
        sql = "select %s from %s %s;" % (names_str, table, where) 
        logger.debug(sql)
        cursor = db.cursor()
        cursor.execute(sql)
        if names == '*':
            names = []
            for name_st in cursor.description:
                names.append(name_st[0])
        items = cursor.fetchall()
        result = []
        for item in items:
            d = {}
            for i, name in enumerate(names):
                d[name] = item[i]
            result.append(d)
        self.done()
        return result
    
    def execute(self, sql):
        db = self.reconnect()
        cursorobj = db.cursor()
        try:
            cursorobj.execute(sql)
            result = cursorobj.fetchall()
            db.commit()
        except Exception:
            raise
        db.close()
        return result
    
    def update(self, table, item):
        '''item is a dict, eg, {id:1, name:'text'}, id is required.'''
        db = self.reconnect()
        rows = []
        item = item.copy()
        id = item['id']
        del item['id']
        for key in item:
            if item[key] != None:
                row = '%s=%s' % (key, escape(item[key]))
            else:
                row = '%s=NULL' % key
            rows.append(row)
        sql = 'update %s set %s where id=%s' % (table, ','.join(rows), id)
        logger.warn(sql)
        db.execute(sql)
        db.commit()
        self.done()
    
    def get_new_id(self):
        data = None
        id = 0
        infos = self.select('pkm_info', '*')
        for info in infos:
            if info['key'] == 'max_id':
                id = int(info['value_start']) + 1
                data = info
                break
        if data:
            data['value_start'] = str(id)
            self.update('pkm_info', data)
        else:
            raise Exception("fatal error, info not found")
        return id
        
    def insert(self, table, d, newid = None):
        if 'id' in d:
            del d['id']
        keys = d.keys()
        values = [str(escape(x)) for x in d.values()]
        if newid == None:
            newid = self.get_new_id()
        sql = 'insert into %s (id, %s) values (%s, %s)' % (table, ','.join(keys), newid, ','.join(values))
        logger.warn(sql)
        db = self.reconnect()
        db.execute(sql)
        db.commit()
        self.done()
        return newid
        
    def search(self, table, d):
        cond = []
        for key in d:
            condition = "%s like %s" % (key, search_escape(d[key]))
            cond.append(condition)
        cond.append("state <> %s" % NO_SEARCH_STATE)
        return self.select(table, '*', ' and '.join(cond))
        # use select * from table where key1 like d[key1] and key2 like d[key2]
        

def run_obj_db_test():
    db = ObjDB('pkm.db')
    d = {"id":7}
    r = db.select("pkm_data", "*", "id=7")
    for i in r:
        print(i)