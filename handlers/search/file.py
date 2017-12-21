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
from xutils import SearchResult
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
    
    @staticmethod
    def fromDict(dict, option=None):
        """build fileDO from dict"""
        name = dict['name']
        file = SearchResult()
        for key in dict:
            file[key] = dict[key]
            # setattr(file, key, dict[key])
        if hasattr(file, "content") and file.content is None:
            file.content = ""
        if option:
            file.option = option
        file.url = "/file/view?id={}".format(dict["id"])
        file.result_type = "file"
        return file

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
    vars = dict()
    for word in words:
        like_list.append('name LIKE %s ' % to_sqlite_obj('%' + word.upper() + '%'))
    sql = "SELECT name, id, ctime, mtime, type, creator FROM file WHERE %s AND is_deleted == 0" % (" AND ".join(like_list))
    if groups and groups != "admin":
        sql += " AND (is_public = 1 OR creator = $creator)"
    sql += " ORDER BY mtime DESC LIMIT 1000";
    vars["creator"] = groups
    all = xtables.get_file_table().query(sql, vars=vars)
    return [FileDO.fromDict(item) for item in all]

def full_search(words, groups=None):
    """ full search the files """
    if not isinstance(words, list):
        words = [words]
    content_like_list = []
    vars = dict()
    # name_like_list = []
    for word in words:
        content_like_list.append('content like %s ' % to_sqlite_obj('%' + word.upper() + '%'))
    # for word in words:
    #     name_like_list.append("related like %s " % repr("%" + word.upper() + '%'))
    sql = "SELECT id, name, ctime, mtime, type, creator FROM file WHERE (%s) AND is_deleted == 0" \
        % " AND ".join(content_like_list)

    if groups and groups != "admin":
        sql += " AND (is_public = 1 OR creator = $creator)"
    sql += " order by mtime desc limit 1000";

    vars["creator"] = groups
    all = xtables.get_file_table().query(sql, vars=vars)
    return [FileDO.fromDict(item) for item in all]

def search(ctx, expression):
    if ctx.search_message and not ctx.search_file_full:
        return
    words = textutil.split_words(expression)
    files = []
    if ctx.search_file_full:
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