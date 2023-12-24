# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# @modified 2021/07/18 19:13:02

"""英汉、汉英词典

dictDTB结构
    _id integer primary key autoincrement,
    en text,cn text,
    symbol text 指音标

"""
import re
import os
import xutils
from xnote.core import xmanager
from xnote.core import xconfig
from xnote.core import xtables
from xutils import u, Storage, SearchResult, textutil
from xnote.core.xtemplate import T

def wrap_results(dicts, origin_key):
    files = []
    for f0 in dicts:
        f = SearchResult()
        f.key = u(f0["key"])
        f.category = "dict"
        f.name = u("翻译 - ") + u(f0[origin_key])
        f.raw = f0["value"].replace("\\n", "\n")
        f.url = "#"
        f.icon = "hide"
        f.id = f0.id
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

# \u7ffb\u8bd1 翻译
# \u5b9a\u4e49 定义
@xmanager.searchable(r"(翻译|定义|define|def|translate)\s+([^\s]+)")
def do_translate(ctx):
    key  = ctx.key
    word = ctx.groups[1]
    word = word.strip().lower()
    path = os.path.join(xconfig.DATA_PATH, "dictionary.db")
    if not os.path.exists(path):
        return
    user_name = ctx.user_name
    table     = xtables.get_dict_table()
    if textutil.isalpha(word):
        dicts = table.select(where="`key` LIKE $key",
            vars = dict(key = word + '%'))
    else:
        dicts = table.select(where="value LIKE $value", 
            vars = dict(value = '%' + word + '%'))
    ctx.dicts += wrap_results(dicts, "key")

@xmanager.searchable(r".+")
def do_translate_strict(ctx):
    if not ctx.search_dict_strict:
        return

    user_name = ctx.user_name
    db = xtables.get_dict_table()
    results = db.select(where="`key` = $key", vars=dict(key=ctx.input_text))
    for item in results:
        value = item.value.replace("\\n", "\n")

        result = Storage()
        result.name = T("search_definition") % item.key
        result.key = item.key
        result.raw = value
        result.url = "#"
        result.icon = "icon-dict"
        result.category = "dict"
        result.id = item.id

        ctx.dicts.append(result)

@xmanager.searchable(r"[a-zA-Z\-]+")
def translate_english(ctx):
    """使用词库进行部分模糊匹配"""
    if not ctx.search_dict:
        return

    user_name = ctx.user_name
    db = xtables.get_dict_table()
    results = db.select(where="key like $key", vars=dict(key=ctx.input_text + "%"))
    for item in results:
        value = item.value.replace("\\n", "\n")

        result = Storage()
        result.name = u("翻译 - %s") % item.key
        result.key = item.key
        result.raw = value
        result.url = "#"
        result.category = "dict"
        result.id = item.id

        ctx.dicts.append(result)




