# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2017/??/??
# @modified 2022/04/10 23:56:20
import os
import sys

import xutils
from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xconfig
from fnmatch import fnmatch
from xutils import dbutil
from xutils import Storage

from .fs_helper import get_index_db

dbutil.register_table("fs_index", "文件索引")

FS = xutils.Module("fs")

def get_fpath_from_key(key):
    left = len("fs_index")+1
    return key[left:]

def clear_file_index():
    index_db = get_index_db()
    for index_obj in index_db.iter():
        # key的格式为 fs_index:fpath
        index_db.delete(index_obj)

def find_in_cache0(key):
    input_key = key.upper()
    plist = []

    def search_file_func(key, value):
        fpath = get_fpath_from_key(key)
        if fnmatch(fpath.upper(), input_key):
            plist.append(fpath)

    dbutil.prefix_list("fs_index", search_file_func)
    return plist

def find_in_cache(key, maxsize=sys.maxsize):
    quoted_key = xutils.quote_unicode(key)
    plist = find_in_cache0(key)
    if quoted_key != key:
        plist += find_in_cache0(quoted_key)
    return plist

def get_index_dirs():
    index_dirs = xauth.get_user_config("admin", "index_dirs")
    return index_dirs.split("\n")

class SearchHandler:

    def GET(self):
        return self.POST()

    @xauth.login_required("admin")
    def POST(self):
        path = xutils.get_argument_str("path")
        if not path:
            path = xconfig.DATA_DIR

        path      = os.path.abspath(path)
        find_key  = xutils.get_argument("find_key", "")
        find_type = xutils.get_argument("type")
        mode      = xutils.get_argument("mode")

        if find_key == "" or find_key is None:
            find_key = xutils.get_argument_str("key", "")
        
        assert isinstance(find_key, str)
        find_key  = "*" + find_key + "*"
        path_name = os.path.join(path, find_key)

        if find_key == "**":
            plist = []
        elif path == os.path.abspath(xconfig.DATA_DIR) and xconfig.USE_CACHE_SEARCH:
            # search in cache
            plist = find_in_cache(find_key)
        else:
            plist = xutils.search_path(path, find_key)

        filelist = FS.process_file_list(plist, path)
        # TODO max result size
        tpl = "fs/page/fs.html"
        if mode == "grid":
            tpl = "fs/fs_grid.html"

        kw = Storage()
        kw.path = path
        kw.quoted_path = xutils.quote(path)
        kw.token = xauth.get_current_user().token
        kw.filelist = filelist

        return xtemplate.render(tpl, **kw)

xurls = (
    r"/fs_find", SearchHandler,
)
