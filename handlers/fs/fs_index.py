# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/08/06 20:28:43
# @modified 2022/04/10 21:45:11
# @filename fs_index.py


"""文件索引处理请查看 `fs_find.py` 
TODO: 文件索引功能开发中
"""

import logging
import os

import xutils
from xutils import Storage
from xutils import dbutil

dbutil.register_table("fs_index", "文件索引")

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
    db = dbutil.get_hash_table("fs_index")
    size = calc_size(db, dirname)
    logging.info("Total size:%s", size)

