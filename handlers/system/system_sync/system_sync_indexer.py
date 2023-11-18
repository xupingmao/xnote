# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/11/28 18:07:31
# @modified 2022/03/18 22:13:48
# @filename system_sync_indexer.py

"""文件同步索引管理器"""

import os
import logging
import time
from collections import deque

import xutils

from xnote.core import xmanager, xconfig, xnote_event, xtables
from xutils import Storage
from xutils import dbutil
from xutils import dateutil
from xutils import fsutil
from xutils import textutil
from xutils.db.binlog import BinLogOpType, FileLog
from handlers.fs.fs_helper import FileInfoDao

_binlog = dbutil.BinLog.get_instance()

# 临时文件
TEMP_FNAME_SET = set([".DS_Store", ".thumbnail", ".git"])

def get_system_role():
    return xconfig.get_global_config("system.node_role")

def print_debug_info(*args):
    new_args = [dateutil.format_time(), "[fs_sync_index]"]
    new_args += args
    print(*new_args)

def convert_time_to_str(mtime):
    return "%020d" % (mtime * 1000)

def is_temp_file(fname):
    return fname in TEMP_FNAME_SET

def build_index_by_fpath(fpath, user_id=0):
    # TODO 如果 user_id=0 尝试根据路径推测用户
    from handlers.fs.fs_helper import FileInfo, FileInfoDao
    st = os.stat(fpath)
    file_info = FileInfo()
    file_info.fpath = fpath
    file_info.user_id = user_id
    file_info.fsize = fsutil.get_file_size_int(fpath)
    file_info.mtime = xutils.format_datetime(st.st_mtime)
    if os.path.isdir(fpath):
        file_info.ftype = "dir"
    else:
        file_info.ftype = fsutil.get_file_ext(fpath)
    FileInfoDao.upsert(file_info)
    logging.debug("更新文件索引:%s", file_info)

class FileSyncIndexManager:

    # 文件队列
    data = deque()
    db = xtables.get_file_info_table()

    def init_file_queue(self):
        logging.debug("初始化文件队列")
        self.data.append(xconfig.get_system_dir("files"))
        self.data.append(xconfig.get_system_dir("storage"))
        self.data.append(xconfig.get_system_dir("app"))
        self.data.append(xconfig.get_system_dir("archive"))
        self.data.append(xconfig.get_system_dir("scripts"))


    def step(self):
        if len(self.data) == 0:
            self.init_file_queue()
            return

        fpath = self.data.popleft()
        if not os.path.exists(fpath):
            logging.error("文件不存在:%s", fpath)
            return

        if os.path.isfile(fpath):
            build_index_by_fpath(fpath)

        if os.path.isdir(fpath):
            size = 0
            for fname in os.listdir(fpath):
                if is_temp_file(fname):
                    continue
                temp_path = os.path.join(fpath, fname)
                self.data.append(temp_path)
                size += 1

            logging.debug("文件夹进队列 fpath:%s, size:%s", fpath, size)
    

    def build_full_index(self):
        self.data.clear()
        self.init_file_queue()
        start_time = time.time()
        while len(self.data) > 0:
            self.step()
        cost_time = time.time() - start_time
        logging.info("构建索引耗时: %0.2fms", cost_time*1000)

    def list_files(self, last_id = 0, offset = 0, limit = 20):
        db = xtables.get_file_info_table()
        result = db.select(where="id > $last_id", vars=dict(last_id=last_id), 
                               offset=offset, limit=limit, order="id")
        for item in result:
            fpath = item.fpath
            if os.path.isdir(fpath):
                item.ftype = "dir"
            item.webpath = fsutil.get_webpath(fpath)
            item.fsize = fsutil.get_file_size_int(fpath)
        return result

    def count_index(self):
        return self.db.count()

class Refrence:

    def __init__(self, value):
        self.value = value

class FileIndexCheckManager:
    """索引检查器"""

    last_check_time = -1
    last_id = 0
    db = xtables.get_table_by_name("file_info")

    def check_index(self, value):
        # type: (Storage) -> bool
        fpath = value.fpath
        index_id = int(value.id)

        if fpath is None:
            logging.debug("check_index:%s", "fpath为空")
            FileInfoDao.delete_by_id(index_id)
            return False
        
        if not os.path.exists(fpath):
            logging.debug("check_index:%s", "文件不存在")
            FileInfoDao.delete_by_id(index_id)
            return False
        
        return True


    def run_step(self):
        where = "id > $id"
        vars = dict(id = self.last_id)
        file_info_list = self.db.select(where=where, vars=vars, order="id", offset=0, limit=20)
        if len(file_info_list) == 0:
            logging.debug("已完成一次全量检查")
        
        for file_info in file_info_list:
            self.check_index(file_info)
            self.last_id = max(self.last_id, file_info.id)

        FileIndexCheckManager.last_check_time = time.time()


@xmanager.listen(["fs.upload", "fs.update"])
def on_fs_upload(ctx: xnote_event.FileUploadEvent):
    logging.debug("检测到文件上传事件: %s", ctx)
    filepath = ctx.fpath
    if filepath == None:
        return
    user_id = ctx.user_id
    build_index_by_fpath(filepath, user_id)

    log_data = FileLog()
    log_data.fpath = filepath
    log_data.user_name = ctx.user_name
    log_data.webpath = fsutil.get_webpath(filepath)
    stat = os.stat(filepath)
    log_data.mtime = stat.st_mtime
    _binlog.add_log("file_upload", filepath, log_data, record_value=True)


@xmanager.listen("fs.remove")
def on_fs_remove(ctx: xnote_event.FileDeleteEvent):
    logging.debug("检测到文件删除事件: %s", ctx)
    from handlers.fs.fs_helper import FileInfoDao
    FileInfoDao.delete_by_fpath(ctx.fpath)

    log_data = FileLog()
    log_data.fpath = ctx.fpath
    log_data.user_name = ctx.user_name
    log_data.webpath = fsutil.get_webpath(ctx.fpath)
    _binlog.add_log(BinLogOpType.file_delete, ctx.fpath, log_data, record_value=True)


@xmanager.listen("fs.rename")
def on_fs_rename(ctx: xnote_event.FileRenameEvent):
    logging.debug("检测到文件重命名事件: %s", ctx)
    from handlers.fs.fs_helper import FileInfoDao

    build_index_by_fpath(ctx.fpath, ctx.user_id)
    FileInfoDao.delete_by_fpath(ctx.old_fpath)

    log_data = FileLog()
    log_data.fpath = ctx.fpath
    log_data.user_name = ctx.user_name
    log_data.webpath = fsutil.get_webpath(ctx.fpath)
    log_data.old_webpath = fsutil.get_webpath(ctx.old_fpath)
    _binlog.add_log(BinLogOpType.file_rename, ctx.fpath, log_data, record_value=True)


def list_files(last_id = 0):
    manager = FileSyncIndexManager()
    return manager.list_files(last_id=last_id)

def count_index():
    manager = FileSyncIndexManager()
    return manager.count_index()

xutils.register_func("system_sync.list_files", list_files)
xutils.register_func("system_sync.count_index", count_index)

