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


def search_tag(ctx: SearchContext, max_result=5):
    from handlers.note.dao_tag import NoteTagInfoDao
    key = ctx.key
    result = [] # type: list[SearchResult]
    if key == "":
        return result
    
    tag_info_list = NoteTagInfoDao.search(user_id=ctx.user_id, tag_code_like=key, order="amount desc")

    tag_result = SearchResult()
    tag_result.name = f"搜索到{len(tag_info_list)}个标签"
    tag_result.url = "#"
    tag_result.icon = "fa fa-tags"
    tag_result.show_move = False
    
    if len(tag_info_list) > 0:
        html = ""
        server_home = xconfig.WebConfig.server_home
        for tag_info in tag_info_list[:max_result]:
            html += f"""<span class="tag-span">
            <a class="tag-link" href="{server_home}{tag_info.url}">{tag_info.tag_name}</a>
            {tag_info.amount}
            </span>"""
        tag_result.html = html
        result.append(tag_result)
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

