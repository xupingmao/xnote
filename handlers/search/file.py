# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# 

"""Description here"""

import sys
import six
import xutils
import xauth
import xmanager
import xconfig
import xtables

from util import textutil

SearchResult = xutils.SearchResult
config = xconfig

def to_sqlite_obj(text):
    if text is None:
        return "NULL"
    if not isinstance(text, six.string_types):
        return repr(text)
    # text = text.replace('\\', '\\')
    text = text.replace("'", "''")
    return "'" + text + "'"
    
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
        t = xutils.format_datetime()
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
            
    @staticmethod
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



def file_dict(id, name, related):
    return dict(id = id, name = name, related = related)

def get_file_db():
    return db.SqliteDB(db=config.DB_PATH)

class FileFilter:

    def __init__(self, file_list = None):
        # self.name_list = name_list
        # self.related_list = related_list
        self._files = {}
        if file_list:
            self._sync_list(file_list)

    def init(self, file_list):
        self._sync_list(file_list)

    def _sync_list(self, file_list):
        for file in file_list:
            self._files[file["id"]] = file

    def _sync(self, id, name, related):
        self._files[id] = [name, related]

    def sync(self, id, file):
        self._files[id] = file

    def search(self, words, hide=True):
        """search file with words"""
        result = []
        for id in self._files:
            file = self._files[id]
            related = file.get("related")
            if hide and textutil.contains(related, "HIDE"):
                continue
            if textutil.contains(related, words):
                result.append(copy.copy(file))
        return result

    def filter(self, fnc):
        result = []
        for id in self._files:
            file = self._files[id]
            if fnc(file):
                result.append(copy.copy(file))
        return result

def search_name(words, groups=None):
    if not isinstance(words, list):
        words = [words]
    like_list = []
    for word in words:
        like_list.append('name LIKE %s ' % to_sqlite_obj('%' + word.upper() + '%'))
    sql = "SELECT * from file WHERE %s AND is_deleted != 1" % (" AND ".join(like_list))
    if groups and groups != "admin":
        sql += " AND (groups = '*' OR groups = '%s')" % groups
    sql += " ORDER BY satime DESC LIMIT 1000";
    # print("search name:", sql)
    all = xtables.get_file_table().query(sql)
    return [FileDO.fromDict(item) for item in all]

def full_search(words, groups=None):
    """ full search the files """
    if not isinstance(words, list):
        words = [words]
    content_like_list = []
    # name_like_list = []
    for word in words:
        content_like_list.append('content like %s ' % to_sqlite_obj('%' + word.upper() + '%'))
    # for word in words:
    #     name_like_list.append("related like %s " % repr("%" + word.upper() + '%'))
    sql = "SELECT * FROM file WHERE (%s) AND is_deleted != 1" \
        % " AND ".join(content_like_list)

    if groups and groups != "admin":
        sql += " AND (groups = '*' OR groups = '%s')" % groups
    sql += " order by satime desc limit 1000";
    # print("full search:", sql)
    all = xtables.get_file_table().query(sql)
    return [FileDO.fromDict(item) for item in all]

def search(expression):
    words = textutil.split_words(expression)
    files = []
    search_content = xutils.get_argument("content")
    if search_content == "on":
        content_results = full_search(words, xauth.get_current_name())
    else:
        content_results = []
    name_results = search_name(words, xauth.get_current_name())
    nameset = set()
    for item in name_results:
        nameset.add(item.name)

    files += name_results

    for item in content_results:
        if item.name not in nameset:
            files.append(item)
    return files

# xmanager.register_search_func(r"(.*)", do_search)