# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/08/06 20:28:43
# @modified 2022/04/10 21:45:11
# @filename fs_index.py

"""文件索引功能"""

import logging
import os
import time

import xauth
import xtemplate
import xconfig
import xmanager
import xutils
from xutils import Storage

from .fs_helpers import get_index_dirs, get_index_db

def calc_dir_size(db, dirname):
    dirname = os.path.abspath(dirname)
    size = 0
    try:
        for fname in os.listdir(dirname):
            fpath = os.path.join(dirname, fname)
            size += calc_size(db, fpath)
    except:
        # 无法读取目录
        xutils.print_exc()

    info = Storage(fsize = size)
    db.put(dirname, info)
    return size


def calc_size(db, fpath):
    fpath = os.path.abspath(fpath)
    print(fpath)
    
    if os.path.islink(fpath):
        # 跳过软连接，避免死循环
        return 0
    
    if os.path.isdir(fpath):
        return calc_dir_size(db, fpath)
    try:
        st = os.stat(fpath)
        info = Storage(fsize = st.st_size)
        db.put(fpath, info)
        return st.st_size
    except:
        xutils.print_exc()
        info = Storage(fsize = -1)
        db.put(fpath, info)
        return 0

def build_fs_index(dirname):
    db = get_index_db()
    size = calc_size(db, dirname)
    logging.info("Total size:%s", size)

def update_file_index():
    # 创建新的索引
    build_fs_index(xconfig.DATA_DIR)

    # 构建外部索引目录的索引
    for dirname in get_index_dirs():
        build_fs_index(dirname)

class IndexHandler:
    """文件索引管理"""

    @xauth.login_required("admin")
    def GET(self):
        user_name = xauth.current_name()
        xmanager.add_visit_log(user_name, "/fs_index")
        path = self.get_arg_path()
        page = xutils.get_argument("p")

        if page == "rebuild":
            return self.get_rebuild_page()

        tpl = "fs/page/fs_index.html"
        index_size = get_index_db().count(prefix = path)
        return xtemplate.render(tpl, 
            index_dirs = get_index_dirs(),
            index_size = index_size)

    @xauth.login_required("admin")
    def POST(self):
        tpl = "fs/page/fs_index.html"
        index_dirs = get_index_dirs()
        cost = 0

        action = xutils.get_argument("action")
        path = self.get_arg_path()
        if action == "reindex":
            cost = self.do_rebuild_index()

        if action == "config":
            return self.do_config()
        
        index_size = get_index_db().count(prefix = path)
        return xtemplate.render(tpl, 
            index_dirs = index_dirs,
            index_size = index_size,
            action = action, 
            cost = cost)
    
    def get_arg_path(self):
        path = xutils.get_argument("path", "")
        if path != "":
            return os.path.abspath(path)
        return path
    
    def do_config(self):
        index_config = xutils.get_argument("index_config")
        xauth.update_user_config(xauth.current_name(), "index_dirs", index_config)
        return dict(code = "success")

    def do_rebuild_index(self):
        path = self.get_arg_path()
        t1 = time.time()

        print("重建索引:", path)

        if path != "":
            build_fs_index(path)
        else:
            update_file_index()
        t2 = time.time()
        return (t2-t1)*1000
    
    def get_rebuild_page(self):
        path = self.get_arg_path()
        db = get_index_db()

        kw = Storage()
        kw.path = path
        kw.show_index_dirs = False
        kw.index_size = db.count(prefix = path)

        return xtemplate.render("fs/page/fs_index.html", **kw)

xurls = (
    r"/fs_index", IndexHandler,
)
