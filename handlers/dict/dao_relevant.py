# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2022-05-01 11:22:35
@LastEditors  : xupingmao
@LastEditTime : 2023-10-06 18:30:36
@FilePath     : /xnote/handlers/dict/dao_relevant.py
"""
import xutils
from xutils import dbutil
from xutils.dateutil import is_str
from xutils.functions import listremove

dbutil.register_table("dict_relevant", "相关词词库", type="hash")
_db = dbutil.get_hash_table("dict_relevant")

class RelevantWord:
    def __init__(self, word, others) -> None:
        self.word = word
        self.others = others

def add_words(words):
    assert isinstance(words, (list, tuple))

    all_words = set(words)
    for word in words:
        record = _db.get(word)
        if record != None:
            all_words.update(record)
    
    all_word_list = list(all_words)
    for word in words:
        word_list_copy = all_word_list.copy()
        listremove(word_list_copy, word)
        _db.put(word, word_list_copy)

def _list_words_by_key(key):
    assert is_str(key)
    assert len(key) > 0

    value = _db.get(key)
    if value == None:
        return 0, []
    else:
        return 1, [RelevantWord(word = key, others = value)]

def list_words(page = 1, pagesize = 20, key = None):
    assert page >= 1
    assert pagesize > 0

    offset = (page-1) * pagesize
    limit = pagesize

    if key != None and key != "":
        return _list_words_by_key(key)
    
    result = []
    for key, value in _db.iter(offset = offset, limit = limit):
        result.append(RelevantWord(word = key, others = value))
    return _db.count(), result

def get_relevant_words(word, exclude_self = True):
    if word == "":
        return []

    word = word.lower()
    words = _db.get(word)
    if words == None:
        return []
    
    if exclude_self:
        listremove(words, word)
    
    return words

def delete_word(word):
    words = get_relevant_words(word)
    for other in words:
        other_words = _db.get(other)
        if other_words != None:
            listremove(other_words, word)
            if len(other_words) == 0:
                _db.delete(other)
            else:
                _db.put(other, other_words)
    _db.delete(word)


xutils.register_func("dict_relevant.add_words", add_words)
xutils.register_func("dict_relevant.list", list_words)
xutils.register_func("dict_relevant.get_relevant_words", get_relevant_words)
xutils.register_func("dict_relevant.delete", delete_word)
