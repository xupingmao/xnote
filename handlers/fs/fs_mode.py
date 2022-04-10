# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2022/04/10 18:30:25
# @modified 2022/04/10 21:49:03
# @filename fs_mode.py

import os
import xtemplate

from xtemplate import T
from xutils import dbutil
from xutils import format_size

_index_db = dbutil.get_hash_table("fs_index")

def get_grid_page(mode, kw):
    return xtemplate.render("fs/page/fs_grid.html", **kw)

def get_default_page(mode, kw):
    return xtemplate.render("fs/page/fs.html", **kw)

def get_sidebar_page(mode, kw):
    kw["show_aside"] = False
    return xtemplate.render("fs/page/fs_sidebar.html", **kw)

def get_size_page(mode, kw):
    filelist = kw.filelist
    for file in filelist:
        fpath = file.path
        fpath = os.path.abspath(fpath)
        info = _index_db.get(fpath)
        if info != None:
            file.fsize = info.fsize
            file.size = format_size(info.fsize)

    def key_func(file):
        if not isinstance(file.fsize, int):
            return 0
        return file.fsize

    filelist.sort(key = key_func, reverse = True)
    kw.fs_title = T("磁盘整理视图")
    return xtemplate.render("fs/page/fs.html", **kw)

MODE_DICT = {
    "grid": get_grid_page,
    "default": get_default_page,
    "sidebar": get_sidebar_page,
    "size": get_size_page,
}

def get_fs_page_by_mode(mode, kw):
    return MODE_DICT.get(mode, get_default_page)(mode, kw)

