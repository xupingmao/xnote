# encoding=utf-8
import os
import json
try:
    import sqlite3
except ImportError:
    sqlite3 = None

try:
    import leveldb
except ImportError:
    leveldb = None

from xconfig import Storage

###########################################################
# @desc db utilties
# @author xupingmao
# @email 578749341@qq.com
# @since 2015-11-02 20:09:44
# @modified 2019/04/27 01:48:41
###########################################################

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
        

# 初始化KV存储
_leveldb = None
if leveldb:
    import xconfig
    _leveldb = leveldb.LevelDB(xconfig.DB_DIR)

def check_leveldb():
    if leveldb is None:
        raise Exception("leveldb not found!")

def get(key):
    check_leveldb()
    try:
        key = key.encode("utf-8")
        value = _leveldb.Get(key)
        obj = json.loads(value.decode("utf-8"))
        if isinstance(obj, dict):
            obj = Storage(**obj)
        return obj
    except KeyError:
        return None

def put(key, obj_value, sync = False):
    check_leveldb()
    
    key = key.encode("utf-8")
    value = json.dumps(obj_value)
    _leveldb.Put(key, value.encode("utf-8"), sync = sync)

def delete(key, sync = False):
    check_leveldb()

    key = key.encode("utf-8")
    _leveldb.Delete(key, sync = sync)

def scan(key_from = None, key_to = None, func = None):
    check_leveldb()

    if key_from:
        key_from = key_from.encode("utf-8")
    if key_to:
        key_to = key_to.encode("utf-8")
    iterator = _leveldb.RangeIter(key_from, key_to, include_value = True)
    for key, value in iterator:
        key = key.decode("utf-8")
        value = json.loads(value.decode("utf-8"))
        func(key, value)

def prefix_scan(prefix, func, reverse = False):
    check_leveldb()

    key_from = None
    key_to = None

    origin_prefix = prefix
    prefix = prefix.encode("utf-8")

    if reverse:
        key_to = prefix
    else:
        key_from = prefix

    iterator = _leveldb.RangeIter(key_from, key_to, include_value = True, reverse = reverse)
    for key, value in iterator:
        key = key.decode("utf-8")
        value = json.loads(value.decode("utf-8"))
        if isinstance(value, dict):
            value = Storage(**value)
        if not func(key, value):
            break

def prefix_list(prefix):
    result = []
    def func(key, value):
        if not key.startswith(prefix):
            return False
        result.append(value)
        return True
    prefix_scan(prefix, func)
    return result

def count(key_from = None, key_to = None, filter_func = None):
    check_leveldb()

    if key_from:
        key_from = key_from.encode("utf-8")
    if key_to:
        key_to = key_to.encode("utf-8")
    iterator = _leveldb.RangeIter(key_from, key_to, include_value = True)
    count = 0
    for key, value in iterator:
        key = key.decode("utf-8")
        value = json.dumps(value.decode("utf-8"))
        if filter_func(key, value):
            count += 1
    return count

def zadd(key, score, member):
    obj = get(key)
    if obj != None:
        obj.pop(member, None)
        obj[member] = score
        put(key, obj)
    else:
        obj = dict()
        obj[member] = score
        put(key, obj)

def zrange(key, start, stop):
    """zset分片，不同于Python，这里是左右包含，包含start，包含stop，默认从小到大排序
    :arg int start: 从0开始，负数表示倒数
    :arg int stop: 从0开始，负数表示倒数
    TODO 优化排序算法，使用有序列表+哈希表
    """
    obj = get(key)
    if obj != None:
        items = obj.items()
        length = len(items)

        if stop < 0:
            stop += length + 1
        if start < 0:
            start += length + 1

        sorted_items = sorted(items, key = lambda x: x[1])
        sorted_keys = [k[0] for k in sorted_items]
        if stop < start:
            # 需要逆序
            stop -= 1
            start += 1
            found = sorted_keys[stop: start]
            found.reverse()
            return found
        return sorted_keys[start: stop]
    return []

def zcount(key):
    obj = get(key)
    if obj != None:
        return len(obj)
    return 0

def zscore(key, member):
    obj = get(key)
    if obj != None:
        return obj.get(member)
    return None

if __name__ == "__main__":
    db = ObjDB('pkm.db')
    d = {"id":7}
    r = db.select("pkm_data", "*", "id=7")
    for i in r:
        print(i)
    
    