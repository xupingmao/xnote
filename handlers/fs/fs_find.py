# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2017/??/??
# @modified 2020/01/22 12:50:12
import os
import sys
import glob
import xutils
import xauth
import xtemplate
import xconfig
import time
from fnmatch import fnmatch

FS = xutils.Module("fs")

def update_file_index():
    xutils.cache_del("fs.list")
    return get_cached_files()


# cache占用内存太多
# @xutils.cache(key="fs.list", expire=-1)
def get_cached_files():
    count = 0
    file_cache = []
    for root, dirs, files in os.walk(xconfig.DATA_DIR):
        for item in dirs:
            path = os.path.join(root, item)
            file_cache.append(path)
            count += 1
        for item in files:
            path = os.path.join(root, item)
            file_cache.append(path)
            count += 1
    xutils.log("files count = {}", count)
    return file_cache

def find_in_cache0(key):
    key = key.upper()
    plist = []
    files = get_cached_files()
    for item in files:
        if fnmatch(item.upper(), key):
            plist.append(item)
    return plist

def find_in_cache(key, maxsize=sys.maxsize):
    quoted_key = xutils.quote_unicode(key)
    plist = find_in_cache0(key)
    if quoted_key != key:
        plist += find_in_cache0(quoted_key)
    return plist

class SearchHandler:

    def GET(self):
        return self.POST()

    @xauth.login_required("admin")
    def POST(self):
        path = xutils.get_argument("path")
        if not path:
            path = xconfig.DATA_DIR

        path      = os.path.abspath(path)
        find_key  = xutils.get_argument("find_key", "")
        find_type = xutils.get_argument("type")
        mode      = xutils.get_argument("mode")

        if find_key == "" or find_key is None:
            find_key = xutils.get_argument("key", "")
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
        tpl = "fs/fs.html"
        if mode == "grid":
            tpl = "fs/fs_grid.html"
        return xtemplate.render(tpl, 
            path  = path,
            token = xauth.get_current_user().token,
            filelist = filelist)

class IndexHandler:
    """文件索引管理"""

    @xauth.login_required("admin")
    def GET(self):
        tpl = "fs/fs_index.html"
        fslist = xutils.cache_get("fs.list")
        if fslist:
            index_size = len(fslist)
        else:
            index_size = 0

        return xtemplate.render(tpl, 
            index_size = index_size,
            show_aside = (xconfig.OPTION_STYLE == "aside"))

    @xauth.login_required("admin")
    def POST(self):
        tpl = "fs/fs_index.html"
        action = xutils.get_argument("action")
        if action == "reindex":
            t1 = time.time()
            fslist = update_file_index()
            t2 = time.time()
            return xtemplate.render(tpl, 
                index_size = len(fslist),
                action = action, 
                cost = (t2-t1)*1000,
                show_aside = (xconfig.OPTION_STYLE == "aside"))
        return self.GET()

xurls = (
    r"/fs_find", SearchHandler,
    r"/fs_index", IndexHandler,
)
