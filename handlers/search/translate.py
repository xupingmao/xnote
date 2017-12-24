# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# 

"""英汉、汉英词典

dictDTB结构
_id integer primary key autoincrement,en text,cn text,symbol text

symbol指音标

"""

import re
import os
import xutils
import xmanager
import xconfig

from xutils import u

SearchResult = xutils.SearchResult

def wrap_results(dicts, origin_key):
    files = []
    for f0 in dicts:
        f = SearchResult()
        f.name = u("翻译 - ") + u(f0[origin_key])
        # f.content = f0["cn"]
        f.raw = f0["en"] + "\n"
        f.raw += f0["cn"].replace("\\n", "\n")
        files.append(f)
    return files

def search(ctx, word):
    """英汉翻译"""
    word = word.lower()
    path = os.path.join(xconfig.DATA_PATH, "dictionary.db")
    if not os.path.exists(path):
        return []
    # COLLATE NOCASE是sqlite的方言
    # 比较通用的做法是冗余字段
    sql = "SELECT * FROM dictTB WHERE en=? COLLATE NOCASE"
    dicts = xutils.db_execute(path, sql, (word,))
    return wrap_results(dicts, "en")

def zh2en(ctx, word):
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