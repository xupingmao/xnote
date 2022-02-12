# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/11/28 18:07:31
# @modified 2022/02/12 18:11:14
# @filename system_sync_indexer.py

"""文件同步索引管理器"""

import os
import logging
import time
from collections import deque

import xmanager
import xutils
import xconfig
from xutils import Storage
from xutils import dbutil
from xutils import dateutil
from xutils import fsutil
from xutils import textutil

dbutil.register_table("fs_sync_index", "文件同步索引信息")

# 临时文件
TEMP_FNAME_SET = set([".DS_Store", ".thumbnail", ".git"])

def get_system_role():
    return xconfig.get_global_config("system.node.role")

def print_debug_info(*args):
    new_args = [dateutil.format_time(), "[fs_sync_index]"]
    new_args += args
    print(*new_args)

def convert_time_to_str(mtime):
    return "%020d" % (mtime * 1000)

def is_temp_file(fname):
    return fname in TEMP_FNAME_SET

class FileSyncIndexManager:

    # 文件队列
    data = deque()

    def init_file_queue(self):
        logging.debug("初始化文件队列")
        self.data.append(xconfig.get_system_dir("files"))
        self.data.append(xconfig.get_system_dir("storage"))


    def step(self):
        if len(self.data) == 0:
            self.init_file_queue()
            return

        db = dbutil.get_table("fs_sync_index", type = "hash")
        fpath = self.data.popleft()
        if not os.path.exists(fpath):
            print_debug_info("文件不存在:", fpath)
            return

        if os.path.isfile(fpath):
            stat = os.stat(fpath)
            mtime = stat.st_mtime
            ts = convert_time_to_str(mtime)
            web_path = fsutil.get_webpath(fpath)
            key = ts + "#" + web_path
            file_size = stat.st_size

            old_info = db.get(key)
            if old_info != None and old_info.ts == ts and old_info.size == file_size:
                print_debug_info("文件已处理:", fpath)
                return

            file_info = Storage()
            file_info.mtime = mtime
            file_info.fpath = fpath
            file_info.web_path = web_path
            file_info.ts = ts
            file_info.size = file_size

            db.put(key, file_info)
            print_debug_info("更新文件索引:", fpath)

        if os.path.isdir(fpath):
            size = 0
            for fname in os.listdir(fpath):
                if is_temp_file(fname):
                    continue
                temp_path = os.path.join(fpath, fname)
                self.data.append(temp_path)
                size += 1

            logging.debug("文件夹进队列 fpath:%s, size:%s", fpath, size)

    def list_files(self, key_from = None, offset = 0, limit = 20):
        result = []
        MAX_LIMIT = limit * 5
        # 这里故意没有用hash_table，是为了使用table的接口
        db = dbutil.get_table("fs_sync_index")

        for value in db.iter(offset = offset, limit = MAX_LIMIT, key_from = key_from):
            fpath = value.fpath
            key   = value._key

            if check_index(key, value, db):
                result.append(value)

            hash_key = textutil.remove_head(key, "fs_sync_index:")
            value.hash_key = hash_key

            if value.ts is None:
                value.ts = convert_time_to_str(value.mtime)

            if len(result) >= limit:
                return result

        return result

    def count_index(self):
        return dbutil.count_table("fs_sync_index")


def check_index(key, value, db):
    fpath = value.fpath

    if fpath is None:
        print_debug_info("check_index", "fpath为空")
        db.delete(value)
        return False
    
    if not os.path.exists(fpath):
        print_debug_info("check_index", "文件不存在")
        db.delete(value)
        return False

    parts = key.split("#")
    if len(parts) != 2:
        print_debug_info("check_index", "key的格式不匹配")
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

    key_from = Refrence("")

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

@xmanager.listen("cron.minute")
def on_build_index(ctx = None):
    if get_system_role() == "follower":
        return

    logging.debug("构建文件同步索引...")
    manager = FileSyncIndexManager()

    for i in range(10):
        manager.step()

def list_files(key_from = None):
    manager = FileSyncIndexManager()
    return manager.list_files(key_from)

def count_index():
    manager = FileSyncIndexManager()
    return manager.count_index()

@xmanager.listen("sync.step")
def on_sync_step(ctx = None):

    tm = time.localtime()
    if tm.tm_sec != 0:
        # logging.debug("未到检查索引时间")
        return

    logging.debug("检查文件同步索引...")
    manager = FileIndexCheckManager()
    for i in range(10):
        manager.step()
    time.sleep(0.1)

xutils.register_func("system_sync.build_index", on_build_index)
xutils.register_func("system_sync.list_files", list_files)
xutils.register_func("system_sync.count_index", count_index)
