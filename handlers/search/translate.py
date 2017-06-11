# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# 

"""Description here"""

import sys
import os

import xutils
import xmanager
import xconfig

SearchResult = xutils.SearchResult

def search(word):
    word = word.lower()
    path = os.path.join(xconfig.DATA_PATH, "dictionary.db")
    if not os.path.exists(path):
        return []
    sql = "SELECT * FROM dictTB WHERE LOWER(en)=?"
    dicts = xutils.db_execute(path, sql, (word,))
    files = []
    for f0 in dicts:
        f = SearchResult()
        f.name = "翻译 - " + f0["en"]
        f.content = f0["cn"]
        f.raw = f0["cn"].replace("\\n", "\n")
        files.append(f)
    return files

# xmanager.register_search_func(r"(.*)", find_translate)