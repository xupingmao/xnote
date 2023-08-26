# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/08/06 20:28:43
# @modified 2022/04/10 21:45:11
# @filename fs_index.py

"""文件索引功能"""

import logging
import os
import time
import threading

import xauth
import xtemplate
import xconfig
import xmanager
import xutils
from xutils import Storage
from xutils.sqldb import TableProxy
from xutils import fsutil
from .fs_helper import get_index_dirs, get_index_db, FileInfoModel, FileInfo

class IndexBuilder:

    _lock = threading.RLock()
    _is_building = False

    def calc_dir_size(self, db, dirname, depth=1000):
        dirname = os.path.abspath(dirname)
        size = 0
        try:
            for fname in os.listdir(dirname):
                fpath = os.path.join(dirname, fname)
                size += self.calc_size(db, fpath, depth-1)
        except:
            # 无法读取目录
            xutils.print_exc()

        info = FileInfo()
        info.fpath = dirname
        info.fsize = size
        info.ftype = "dir"
        FileInfoModel.upsert(info)
        return size


    def calc_size(self, db, fpath, depth=1000): 
        # type: (TableProxy, str, int) -> int
        if depth <= 0:
            logging.error("too deep depth")
            return 0
        
        if os.path.islink(fpath):
            # 软链接会导致循环引用,即使用真实的路径也不能解决这个问题
            return 0

        fpath = os.path.realpath(fpath)
        logging.info("fs_index path: %s", fpath)

        if os.path.isdir(fpath):
            return self.calc_dir_size(db, fpath, depth-1)
        try:
            st = os.stat(fpath)
            info = FileInfo()
            info.fsize = st.st_size
            info.fpath = fpath
            info.ctime = xutils.format_datetime(st.st_ctime)
            info.mtime = xutils.format_datetime(st.st_mtime)
            info.ftype = fsutil.get_file_ext(fpath)
            FileInfoModel.upsert(info)
            return st.st_size
        except:
            xutils.print_exc()
            info = FileInfo()
            info.fsize = -1
            info.fpath = fpath
            FileInfoModel.upsert(info)
            return 0

    @classmethod
    def build_fs_index(cls, dirname, sync=False):
        with cls._lock:
            if cls._is_building:
                raise Exception("正在构建索引，请稍后重试")
            
            if sync:
                return cls.do_build_index(dirname)
            else:
                return cls.build_fs_index_async(dirname)

    @classmethod
    @xutils.async_func_deco()
    def build_fs_index_async(cls, dirname):
        return cls.do_build_index(dirname)
    
    @classmethod
    def do_build_index(cls, dirname):
        cls._is_building = True
        try:
            builder = IndexBuilder()
            db = get_index_db()
            size = builder.calc_size(db, dirname)
            logging.info("Total size:%s", size)
            return size
        finally:
            cls._is_building = False
        

def build_fs_index(dirname, sync=False):
    return IndexBuilder.build_fs_index(dirname, sync)


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
        user_name = xauth.current_name_str()
        xmanager.add_visit_log(user_name, "/fs_index")
        path = self.get_arg_path()
        page = xutils.get_argument("p")

        if page == "rebuild":
            return self.get_rebuild_page()

        tpl = "fs/page/fs_index.html"
        index_size = FileInfoModel.prefix_count(path)
        return xtemplate.render(tpl, 
            index_dirs = get_index_dirs(),
            index_size = index_size)

    @xauth.login_required("admin")
    def POST(self):
        is_ajax = xutils.get_argument_bool("is_ajax", False)
        tpl = "fs/page/fs_index.html"
        index_dirs = get_index_dirs()
        cost = 0

        action = xutils.get_argument("action")
        path = self.get_arg_path()
        err = ""
        index_size = 0

        try:
            if action == "reindex":
                cost = self.do_rebuild_index()

            if action == "config":
                return self.do_config()
            
            index_size = FileInfoModel.prefix_count(path)
        except Exception as e:
            xutils.print_exc()
            err = str(e)

        if is_ajax:
            if err != "":
                return dict(code="500", message=err)
            return dict(code="success", data = index_size)

        return xtemplate.render(tpl, 
            index_dirs = index_dirs,
            index_size = index_size,
            action = action, 
            cost = cost)
    
    def create_kw(self):
        kw = Storage()
        embed = xutils.get_argument_bool("embed", False)
        if embed:
            kw.show_nav = False
        return kw
    
    def get_arg_path(self):
        path = xutils.get_argument_str("path", "")
        if path != "":
            return os.path.abspath(path)
        return path
    
    def do_config(self):
        index_config = xutils.get_argument("index_config")
        xauth.update_user_config(xauth.current_name(), "fs_index_dirs", index_config)
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
        kw = self.create_kw()
        kw.path = path
        kw.show_index_dirs = False
        kw.index_size = FileInfoModel.prefix_count(path)

        return xtemplate.render("fs/page/fs_index.html", **kw)

xurls = (
    r"/fs_index", IndexHandler,
)
