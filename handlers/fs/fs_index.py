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
import xutils

from xnote.core import xauth
from xnote.core import xtemplate
from xnote.core import xconfig
from xnote.core import xmanager
from xutils import Storage
from xutils.sqldb import TableProxy
from xutils import fsutil, webutil
from .fs_helper import get_index_dirs, get_index_db, FileInfoDao, FileInfo
from xnote.plugin.table_plugin import BaseTablePlugin
from xnote.plugin import sidebar

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
        FileInfoDao.upsert(info)
        return size


    def calc_size(self, db, fpath: str, depth=1000): 
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
            self.upsert_file_index(info)
            return st.st_size
        except:
            xutils.print_exc()
            info = FileInfo()
            info.fsize = -1
            info.fpath = fpath
            self.upsert_file_index(info)
            return 0
        
    def upsert_file_index(self, info: FileInfo):
        if not fsutil.is_parent_dir(xconfig.FileConfig.data_dir, info.fpath):
            logging.info("not in data dir, skip, fpath=%s", info.fpath)
            return
        return FileInfoDao.upsert(info)

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
    is_data_dir = fsutil.is_same_file(dirname, xconfig.FileConfig.data_dir)
    is_sub_dir = fsutil.is_parent_dir(xconfig.FileConfig.data_dir, dirname)
    is_valid_dir = is_data_dir or is_sub_dir
    if not is_valid_dir:
        raise Exception("只允许构建 /data 目录的文件索引")
    return IndexBuilder.build_fs_index(dirname, sync)


def update_file_index():
    # 创建新的索引
    build_fs_index(xconfig.FileConfig.data_dir)

class IndexHandler(BaseTablePlugin):
    """文件索引管理"""

    title = "索引管理"
    require_admin = True
    show_aside = True

    NAV_HTML = ""

    action_bar_html = """
    {% init index_size = 0 %}
    <div class="table-action-row">
        <button class="btn" onclick="xnote.table.handleConfirmAction(this)"
            data-url="?action=rebuild" data-msg="确定要重建索引吗?">重建索引</button>
        <span>索引数量: {{index_size}}</span>
    </div>
    """

    def get_aside_html(self):
        return sidebar.get_fs_sidebar_html()

    def handle_page(self):
        table = self.create_table()
        table.default_head_style.min_width = "100px"
        table.add_head("文件编号", "id")
        table.add_head("文件路径", "fpath")
        table.add_head("用户ID", "user_id")
        table.add_head("上传时间", "ctime", min_width="200px")
        table.add_head("文件大小", "fsize_str")

        page = xutils.get_argument_int("page",1)
        user_name = xauth.current_name_str()
        xmanager.add_visit_log(user_name, "/fs_index")
        path = self.get_arg_path()
        page_size = 20
        index_size = FileInfoDao.prefix_count(path)
        page_info = webutil.Pagination(page=page, total=index_size, page_size=page_size)
        offset = (page-1) * page_size
        
        files = FileInfoDao.list(offset=offset, limit=20, is_admin=True)
        for file_info in files:
            file_info.fsize_str = "-"
            if isinstance(file_info.fsize, int):
                file_info.fsize_str = fsutil.format_size(file_info.fsize)

            table.add_row(file_info)
                
        table.action_bar_html = xtemplate.render_text(self.action_bar_html, index_size=index_size)
        kw = Storage()
        kw.table = table
        kw.index_size = index_size
        kw.files = files
        kw.index_dirs = get_index_dirs()
        kw.page = page
        kw.page_max = page_info.page_max
        kw.page_url = f"?page="
        return self.response_page(**kw)
    
    def handle_rebuild(self):
        self.do_rebuild_index()
        return webutil.SuccessResult()

    def do_post(self):
        is_ajax = xutils.get_argument_bool("is_ajax", False)
        tpl = "fs/page/fs_index.html"
        index_dirs = get_index_dirs()
        cost = 0

        action = xutils.get_argument_str("action")
        path = self.get_arg_path()
        err = ""
        index_size = 0

        try:
            if action == "reindex":
                cost = self.do_rebuild_index()

            if action == "config":
                return self.do_config()
            
            index_size = FileInfoDao.prefix_count(path)
        except Exception as e:
            xutils.print_exc()
            err = str(e)

        if is_ajax:
            if err != "":
                return webutil.FailedResult(code="500", message=err)
            return webutil.SuccessResult(data = index_size)
        
        kw = Storage()
        kw.index_dirs = index_dirs
        kw.index_size = index_size
        kw.action = action
        kw.cost = cost
        kw.err = err

        return xtemplate.render(tpl, **kw)
    
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
        return webutil.SuccessResult()

    def do_rebuild_index(self):
        path = self.get_arg_path()
        t1 = time.time()

        logging.info("重建索引:%s", path)

        if path != "":
            build_fs_index(path)
        else:
            update_file_index()
        t2 = time.time()
        return (t2-t1)*1000


xurls = (
    r"/fs_index", IndexHandler,
)
