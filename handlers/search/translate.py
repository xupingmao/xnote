# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# 

"""英汉、汉英词典

dictDTB结构
_id integer primary key autoincrement,en text,cn text,symbol text

symbol指音标

"""

import sys
import os

import xutils
import xmanager
import xconfig

SearchResult = xutils.SearchResult

def wrap_results(dicts, origin_key):
    files = []
    for f0 in dicts:
        f = SearchResult()
        f.name = "翻译 - " + f0[origin_key]
        # f.content = f0["cn"]
        f.raw = f0["en"] + "\n"
        f.raw += f0["cn"].replace("\\n", "\n")
        files.append(f)
    return files

def search(word):
    word = word.lower()
    path = os.path.join(xconfig.DATA_PATH, "dictionary.db")
    if not os.path.exists(path):
        return []
    sql = "SELECT * FROM dictTB WHERE LOWER(en)=?"
    dicts = xutils.db_execute(path, sql, (word,))
    return wrap_results(dicts, "en")

def zh2en(word):
    word = word.lower()
    path = os.path.join(xconfig.DATA_PATH, "dictionary.db")
    if not os.path.exists(path):
        return []
    sql = "SELECT * FROM dictTB WHERE cn LIKE ?"
    dicts = xutils.db_execute(path, sql, ('%' + word,))
    if len(dicts) > 0:
        return wrap_results(dicts, "cn")
    sql = "SELECT * FROM dictTB WHERE cn LIKE ?"
    dicts = xutils.db_execute(path, sql, ('%' + word + '%',))
    return wrap_results(dicts, "cn")

# xmanager.register_search_func(r"(.*)", find_translate)