# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
# @modified 2022/03/08 23:05:51
"""搜索知识库文件"""
import re
import sys
import logging

import xutils
from xnote.core import xauth
from xnote.core import xmanager
from xnote.core import xconfig
from xnote.core import xtables
from xnote.core.models import SearchContext
from xutils import textutil
from xutils import SearchResult, text_contains

def filter_symbols(words):
    new_words = []
    for word in words:
        word = re.sub("。", "", word)
        if word == "":
            continue
        new_words.append(word)
    return new_words


def search_tag(ctx: SearchContext):
    from handlers.note.dao_tag import NoteTagInfoDao
    key = ctx.key
    result = [] # type: list[SearchResult]
    if key == "":
        return result
    
    tag_info = NoteTagInfoDao.get_by_code(user_id=ctx.user_id, tag_code=key)
    if tag_info != None:
        tag_result = SearchResult()
        tag_result.name = f"【标签】{tag_info.tag_name}"
        tag_result.url = tag_info.url
        tag_result.icon = "fa fa-file-text-o"
        tag_result.show_move = False
        result.append(tag_result)
        return result
    return result


def search(ctx: SearchContext, expression=None):
    from handlers.note import dao as note_dao
    words = ctx.words
    files = []
    tags = search_tag(ctx)

    words = filter_symbols(words)

    if len(words) == 0:
        return files

    if ctx.search_note_content:
        files += note_dao.search_content(words, xauth.current_name_str())
    
    if ctx.search_note:
        files += note_dao.search_name(words, xauth.current_name_str())

    for item in files:
        item.category = 'note'

    # group 放前面
    groups = list(filter(lambda x: x.type == "group", files))
    text_files = list(filter(lambda x: x.type != "group", files))
    files = groups + text_files

    logging.debug("len(files)=%s", len(files))
    return tags + files

