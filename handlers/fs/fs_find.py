# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2017/??/??
# @modified 2021/02/27 16:09:15
import os
import sys
import glob
import xutils
import xauth
import xtemplate
import xconfig
import xmanager
import time
from fnmatch import fnmatch
from xutils import dbutil


dbutil.register_table("fs_index", "文件索引")

FS = xutils.Module("fs")

def rebuild_file_index(dirname):
    count = 0
    # 构建新的索引
    for root, dirs, files in os.walk(dirname):
        for item in dirs:
            path = os.path.join(root, item)
            dbutil.put("fs_index:%s" % path, "1")
            count += 1
        for item in files:
            path = os.path.join(root, item)
            dbutil.put("fs_index:%s" % path, "1")
            count += 1
    xutils.log("files count = {}", count)

def get_fpath_from_key(key):
    left = len("fs_index") + 1
    return key[left:]

def clear_file_index():
    for key, value in dbutil.prefix_iter("fs_index", include_key = True):
        # key的格式为 fs_index:fpath
        dbutil.delete(key)

def update_file_index():
    # 清理旧的索引
    clear_file_index()

    # 创建新的索引
    rebuild_file_index(xconfig.DATA_DIR)

    # 构建外部索引目录的索引
    for dirname in get_index_dirs():
        rebuild_file_index(dirname)

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
    return xauth.get_user_config_dict("admin").get("index_dirs", [])

def update_index_config(index_config):
    index_dirs = set()
    config_list = index_config.split("\n")
    for fpath in config_list:
        fpath = fpath.strip()
        if os.path.exists(fpath):
            index_dirs.add(fpath)

    config_dict = dict(index_dirs = list(index_dirs))
    xauth.update_user_config_dict("admin", config_dict)


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
        tpl = "fs/page/fs.html"
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
        user_name = xauth.current_name()
        xmanager.add_visit_log(user_name, "/fs_index")

        tpl = "fs/fs_index.html"
        index_size = dbutil.count_table("fs_index")
        return xtemplate.render(tpl, 
            index_dirs = get_index_dirs(),
            index_size = index_size)

    @xauth.login_required("admin")
    def POST(self):
        tpl = "fs/fs_index.html"
        index_dirs = get_index_dirs()
        cost = 0

        action = xutils.get_argument("action")
        if action == "reindex":
            t1 = time.time()
            update_file_index()
            t2 = time.time()
            cost = (t2-t1)*1000


        if action == "config":
            index_config = xutils.get_argument("index_config")
            update_index_config(index_config)
            index_dirs = get_index_dirs()
        
        index_size = dbutil.count_table("fs_index")
        return xtemplate.render(tpl, 
            index_dirs = index_dirs,
            index_size = index_size,
            action = action, 
            cost = cost)

xutils.register_func("fs.get_index_dirs", get_index_dirs)

xurls = (
    r"/fs_find", SearchHandler,
    r"/fs_index", IndexHandler,
)
