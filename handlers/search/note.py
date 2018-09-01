# -*- coding:utf-8 -*-  
# Created by xupingmao on 2017/06/11
"""搜索知识库文件"""
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

def get_file_db():
    return db.SqliteDB(db=config.DB_PATH)

def get_cached_notes0():
    return list(xtables.get_file_table().query('SELECT name, UPPER(name) as name_upper, id, parent_id, ctime, mtime, type, creator, is_public FROM file WHERE is_deleted == 0'))


@xutils.cache(key='note_name.list', expire=3600)
def get_cached_notes():
    return get_cached_notes0()

def search_in_cache(words, user):
    def fmap(word):
        return word.upper()
    words = list(map(fmap, words))
    hits = []
    for item in get_cached_notes():
        if item.name is None:
            continue
        if user != item.creator and user != 'admin' and item.is_public == 0:
            continue
        if text_contains(item.name_upper, words):
            item = file_wrapper(item)
            hits.append(item)
    return sorted(hits, key=lambda x: x.mtime, reverse=True)

def search_name(words, groups=None):
    if not isinstance(words, list):
        words = [words]
    if xconfig.USE_CACHE_SEARCH:
        return search_in_cache(words, groups)
    like_list = []
    vars = dict()
    for word in words:
        like_list.append('name LIKE %s ' % to_sqlite_obj('%' + word.upper() + '%'))
    sql = "SELECT name, id, parent_id, ctime, mtime, type, creator FROM file WHERE %s AND is_deleted == 0" % (" AND ".join(like_list))
    if groups != "admin":
        sql += " AND (is_public = 1 OR creator = $creator)"
    sql += " ORDER BY mtime DESC LIMIT 1000";
    vars["creator"] = groups
    all = xtables.get_file_table().query(sql, vars=vars)
    return [file_wrapper(item) for item in all]

def full_search(words, groups=None):
    """ full search the files """
    if not isinstance(words, list):
        words = [words]
    content_like_list = []
    vars = dict()
    for word in words:
        content_like_list.append('note_content.content like %s' % to_sqlite_obj('%' + word.upper() + '%'))
    sql = "SELECT file.id AS id, file.parent_id AS parent_id, file.name AS name, file.ctime AS ctime, file.mtime AS mtime, file.type AS type, file.creator AS creator FROM file JOIN note_content ON file.id = note_content.id WHERE file.is_deleted == 0 AND "
    sql += " AND ".join(content_like_list)
    if groups != "admin":
        sql += " AND (file.is_public = 1 OR file.creator = $creator)"
    sql += " order by mtime desc limit 1000"
    print(sql)

    vars["creator"] = groups
    all = xtables.get_file_table().query(sql, vars=vars)
    return [file_wrapper(item) for item in all]

def search(ctx, expression=None):
    words = ctx.words
    files = []

    if ctx.search_file_full:
        files += full_search(words, xauth.get_current_name())
    
    if ctx.search_file:
        files += search_name(words, xauth.get_current_name())

    # group 放前面
    groups = list(filter(lambda x: x.type == "group", files))
    text_files  = list(filter(lambda x: x.type != "group", files))
    files = groups + text_files
    return files

@xmanager.listen(["note.rename", "note.add", "note.remove"], is_async=True)
def update_cached_notes(file):
    if not xconfig.USE_CACHE_SEARCH:
        return
    xutils.update_cache("note_name.list", get_cached_notes0())

# 初始化缓存
if xconfig.USE_CACHE_SEARCH:
    get_cached_notes()

