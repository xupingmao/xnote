# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# @modified 2022/03/08 23:05:51
"""搜索知识库文件"""
import re
import sys
import six
import logging

import xutils
import xauth
import xmanager
import xconfig
import xtables
from xutils import textutil
from xutils import SearchResult, text_contains

NOTE_DAO = xutils.DAO("note")

def to_sqlite_obj(text):
    if text is None:
        return "NULL"
    if not isinstance(text, six.string_types):
        return repr(text)
    text = text.replace("'", "''")
    return "'" + text + "'"
    
def filter_symbols(words):
    new_words = []
    for word in words:
        word = re.sub("。", "", word)
        if word == "":
            continue
        new_words.append(word)
    return new_words

def search(ctx, expression=None):
    words = ctx.words
    files = []

    words = filter_symbols(words)

    if len(words) == 0:
        return files

    if ctx.search_note_content:
        files += NOTE_DAO.search_content(words, xauth.current_name())
    
    if ctx.search_note:
        files += NOTE_DAO.search_name(words, xauth.current_name())

    for item in files:
        item.category = 'note'

    # group 放前面
    groups     = list(filter(lambda x: x.type == "group", files))
    text_files = list(filter(lambda x: x.type != "group", files))
    files      = groups + text_files

    logging.debug("len(files)=%s", len(files))
    return files

