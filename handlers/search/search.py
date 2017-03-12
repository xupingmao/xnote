# encoding=utf-8
import re
import os
import sys
import copy

import web
import xutils
from FileDB import FileDO
from handlers.base import *
import web.db as db

"""FileDB cache"""

def file_dict(id, name, related):
    return dict(id = id, name = name, related = related)

def get_file_db():
    return db.SqliteDB(db="db/data.db")

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

def do_search(words, key=None):
    files = []

    if len(words) == 1:
        translates = find_translate(words[0])
        tools = find_tools(words[0])
        pydocs = find_py_docs(words[0])
        files += translates + tools + pydocs

    name_results = FileDB.search_name(words)
    # FileDB.full_search(context, words)
    # files = self._service.search(words)
    content_results = FileDB.full_search(words)

    nameset = set()
    for item in name_results:
        nameset.add(item.name)

    files += name_results

    for item in content_results:
        if item.name not in nameset:
            files.append(item)
    return files[:20]

def find_py_docs(name):
    """搜索Python文档"""
    if name in sys.modules:
        item = FileDO("Python Document - %s" % name)
        item.url = "/system/doc?name=%s" % name
        item.content = ""
        return [item]
    return []

def do_calc(words, key):
    exp = " ".join(words[1:])
    try:
        value = eval(exp)
        f = FileDO("计算结果")
        f.content = str(value)
        return [f]
    except Exception as e:
        print(e)
        return []

def try_calc(words, key):
    exp = key
    try:
        value = eval(exp)
        f = FileDO("计算结果")
        f.content = str(value)
        return [f] + do_search(words, key)
    except Exception as e:
        print(e)
        return do_search(words, key)

def find_tools(name):
    """查找`handlers/tools/`目录下的工具"""
    tools_path = config.TOOLS_DIR
    files = []
    for filename in os.listdir(tools_path):
        _filename, ext = os.path.splitext(filename)
        if filename.endswith(".html") and name in _filename:
            f = FileDO("工具 - " + filename)
            f.url = "/tools/" + filename
            f.content = filename
            files.append(f)
    return files

def find_translate(word):
    word = word.lower()
    path = "db/dictionary.db"
    if not os.path.exists(path):
        return []
    sql = "select * from dictTB where LOWER(en)=?"
    dicts = xutils.db_execute(path, sql, (word,))
    files = []
    for f0 in dicts:
        f = FileDO("翻译 - " + f0["en"])
        f.content = f0["cn"]
        f.raw = f0["cn"].replace("\\n", "\n")
        files.append(f)
    return files

def do_tools(words, key):
    name = words[1]
    return find_tools(name)

class handler(BaseHandler):
    mappings = (
        r"search.*", do_search,
        r"calc.*", do_calc,
        r".*[0-9]+.*", try_calc,
    )

    def search_models(self, words):
        modelManager = config.get("modelManager")
        if modelManager is not None:
            return modelManager.search(words)
        return []

    def _match(self, key):
        for i in range(0, len(self.mappings), 2):
            pattern = self.mappings[i]
            func = self.mappings[i+1]
            if re.match(pattern, key):
                return func
        return None


    def full_search(self, key):
        if key is None or key == "":
            files = []
        else:
            words = textutil.split_words(key)
            op = words[0]
            func = self._match(key)
            if func:
                files = func(words, key)
            else:
                files = do_search(words, key)
        return files
        # self.render("file-list.html", key = key, 
        #     files = files, count=len(files), full_search="on")

    def json_request(self):
        key = self.get_argument("key", "").strip()
        if key == "":
            raise web.seeother("/")
        return self.full_search(key)


    """ search files by name and tags """
    def default_request(self):
        key = self.get_argument("key", None)
        full_search = self.get_argument("full_search", None)
        # if full_search == "on":
        #     return self.full_search();
        if key is None or key == "":
            raise web.seeother("/")
        else:
            files = self.full_search(key)
        self.render("file-list.html", key = key, 
            files = files, count=len(files))

name = "搜索"
description = "xnote搜索，可以搜索笔记、工具"