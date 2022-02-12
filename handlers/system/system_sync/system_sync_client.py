# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/11/29 22:48:26
# @modified 2022/01/27 21:44:30
# @filename system_sync_http.py

import os
import xutils
import xconfig
import logging
from xutils import Storage
from xutils import netutil
from xutils import textutil
from xutils import dateutil
from xutils import fsutil
from xutils import dbutil
from xutils.imports import quote

dbutil.register_table("fs_sync_index_copy", "文件索引拷贝")
dbutil.register_table("fs_sync_index_failed", "文件索引拷贝失败")

def print_debug_info(*args):
    new_args = [dateutil.format_time(), "[system_sync_http]"]
    new_args += args
    print(*new_args)

class HttpClient:

    def __init__(self, host, token, admin_token):
        self.host = host
        self.token = token
        self.admin_token = admin_token

    def get_table(self):
        return dbutil.get_hash_table("fs_sync_index_copy")

    def get_failed_table(self):
        return dbutil.get_hash_table("fs_sync_index_failed")

    def get_stat(self, params):
        self.check_disk_space()

        params["token"] = self.token

        url = "{host}/system/sync?p=get_stat".format(host = self.host)
        result = netutil.http_get(url, params = params)
        result_obj = textutil.parse_json(result, ignore_error = True)
        return result_obj    

    def list_files(self, offset):
        url = "{host}/system/sync?p=list_files&token={token}&offset={offset}".format(
            host = self.host, token = self.token, offset = quote(offset))

        content = netutil.http_get(url)
        result = textutil.parse_json(content, ignore_error = True)
        if result is None:
            error = Storage()
            error.url = url
            error.content = content
            print_debug_info("接口返回为空", error)
            return

        result = Storage(**result)
        if result.code != "success":
            print_debug_info("接口请求失败", result)

        follower_dict = result.get("follower_dict", {})
        for url in follower_dict:
            info = follower_dict.get(url)
            self.admin_token = info.get("admin_token")

        return result

    def is_same_file(self, dest_path, item):
        if not os.path.exists(dest_path):
            return False

        stat = os.stat(dest_path)
        return item.size == stat.st_size and item.mtime == stat.st_mtime

    def check_disk_space(self):
        data_dir = xconfig.get_system_dir("data")
        free_space = fsutil.get_free_space(data_dir)
        result = free_space >= 1024 ** 3 # 要大于1G

        if not result:
            logging.debug("磁盘容量不足, 当前容量:%s", fsutil.format_size(free_space))

        return result

    def download_file(self, item):
        if self.admin_token is None:
            logging.warn("admin_token为空，跳过")
            return

        if not self.check_disk_space():
            logging.error("磁盘容量不足，跳过")
            return

        fpath = item.fpath
        web_path = item.web_path
        mtime = item.mtime

        # 保存文件索引信息
        table = self.get_table()
        table.put(web_path, item)

        encoded_fpath = xutils.urlsafe_b64encode(fpath)
        url = "{host}/fs_download".format(host = self.host)
        params = dict(token = self.admin_token, fpath = encoded_fpath)
        url = netutil._join_url_and_params(url, params)

        data_dir  = xconfig.get_system_dir("data")
        temp_path = fsutil.get_relative_path(web_path, "/data/")
        dest_path = os.path.join(data_dir, temp_path)
        dirname   = os.path.dirname(dest_path)

        if self.is_same_file(dest_path, item):
            logging.debug("文件没有变化，跳过:%s", web_path)
            return

        fsutil.makedirs(dirname)

        logging.debug("原始文件:%s", url)
        logging.debug("目标文件:%s", dest_path)

        try:
            netutil.http_download(url, dest_path)
            os.utime(dest_path, times=(mtime, mtime))
        except:
            xutils.print_exc()
            logging.error("下载文件失败:%s", dest_path)
            self.get_failed_table().put(web_path, item)

    def download_files(self, result):
        for item in result.data:
            self.download_file(Storage(**item))

xutils.register_func("system_sync.HttpClient", HttpClient)

