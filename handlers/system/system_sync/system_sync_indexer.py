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

import xmanager
import xutils
import xconfig
import xnote_event
import xtables
from xutils import Storage
from xutils import dbutil
from xutils import dateutil
from xutils import fsutil
from xutils import textutil

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
    file_info = FileInfo()
    file_info.fpath = fpath
    file_info.user_id = user_id
    file_info.fsize = fsutil.get_file_size_int(fpath)
    file_info.mtime = xutils.format_datetime()
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
            item.web_path = fsutil.get_webpath(fpath)
        return result

    def count_index(self):
        return self.db.count()


def check_index(key, value, db):
    fpath = value.fpath

    if fpath is None:
        logging.debug("check_index:%s", "fpath为空")
        db.delete(value)
        return False
    
    if not os.path.exists(fpath):
        logging.debug("check_index:%s", "文件不存在")
        db.delete(value)
        return False

    parts = key.split("#")
    if len(parts) != 2:
        logging.debug("check_index:%s", "key的格式不匹配")
        db.delete(value)
        return False

    if parts[1] != value.web_path:
        logging.debug("check_index:%s", "web_path不匹配")
        db.delete(value)
        return False

    if value.size is None or value.mtime is None or value.ts is None:
        logging.debug("check_index:%s", "关键信息缺失")
        db.delete(value)
        return False

    return True


class Refrence:

    def __init__(self, value):
        self.value = value

class FileIndexCheckManager:
    """索引检查器"""

    key_from = Refrence("")
    last_check_time = -1

    def get_key_from(self):
        return self.key_from.value

    def update_key_from(self, value):
        self.key_from.value = value

    def step(self):
        key_from_copy = self.get_key_from()

        db = dbutil.get_table("fs_sync_index")
        for value in db.iter(offset = 0, limit = 10, key_from = self.get_key_from()):
            key = value._key
            check_index(key, value, db)

            if value.ts != None:
                self.update_key_from(value.ts)

        if self.get_key_from() != "" and self.get_key_from() == key_from_copy:
            logging.debug("已完成一次全量检查")
            self.update_key_from("")

        FileIndexCheckManager.last_check_time = time.time()

@xmanager.listen("fs.rename")
def on_fs_rename(event: dict):
    user = event.get("user")
    fpath = event.get("path")
    old_path = event.get("old_path")
    if fpath == None:
        return

    log_data = Storage()
    log_data = Storage()
    log_data.fpath = fpath
    log_data.user = user
    log_data.web_path = fsutil.get_webpath(fpath)
    stat = os.stat(fpath)
    log_data.mtime = stat.st_mtime

    old_value = Storage()
    old_value.fpath = old_path

    _binlog.add_log("file_rename", fpath, log_data, old_value = old_value, record_value=True)


@xmanager.listen(["fs.upload", "fs.update"])
def on_fs_upload(ctx: xnote_event.FileUploadEvent):
    logging.debug("检测到文件上传信息:%s", ctx)
    filepath = ctx.fpath
    if filepath == None:
        return
    user_id = ctx.user_id
    build_index_by_fpath(filepath, user_id)

    log_data = Storage()
    log_data.fpath = filepath
    log_data.user = ctx.user_name
    log_data.web_path = fsutil.get_webpath(filepath)
    stat = os.stat(filepath)
    log_data.mtime = stat.st_mtime
    _binlog.add_log("file_upload", filepath, log_data, record_value=True)

def list_files(last_id = 0):
    manager = FileSyncIndexManager()
    return manager.list_files(last_id=last_id)

def count_index():
    manager = FileSyncIndexManager()
    return manager.count_index()

xutils.register_func("system_sync.list_files", list_files)
xutils.register_func("system_sync.count_index", count_index)

