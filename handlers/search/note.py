# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# @modified 2019/04/29 21:54:40
"""搜索知识库文件"""
import re
import sys
import six
import xutils
import xauth
import xmanager
import xconfig
import xtables
from xutils import textutil
from xutils import SearchResult, text_contains
config = xconfig

def to_sqlite_obj(text):
    if text is None:
        return "NULL"
    if not isinstance(text, six.string_types):
        return repr(text)
    text = text.replace("'", "''")
    return "'" + text + "'"
    
def file_wrapper(dict, option=None):
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
    file.url = "/note/view?id={}".format(dict["id"])
    # 文档类型，和文件系统file区分
    file.category = "note"
    return file

def file_dict(id, name, related):
    return dict(id = id, name = name, related = related)

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
        files += xutils.call("note.search_content", words, xauth.current_name())
    
    if ctx.search_note:
        files += xutils.call("note.search_name", words, xauth.current_name())

    # group 放前面
    groups = list(filter(lambda x: x.type == "group", files))
    text_files  = list(filter(lambda x: x.type != "group", files))
    files = groups + text_files
    return files

