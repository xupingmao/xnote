# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2021/11/29 22:48:26
# @modified 2021/12/05 11:04:16
# @filename system_sync_http.py

import os
import xutils
import xconfig
from xutils import Storage
from xutils import netutil
from xutils import textutil
from xutils import dateutil
from xutils import fsutil

def print_debug_info(*args):
    new_args = [dateutil.format_time(), "[system_sync_http]"]
    new_args += args
    print(*new_args)

class HttpClient:

    def __init__(self, host, token, admin_token):
        self.host = host
        self.token = token
        self.admin_token = admin_token

    def get_stat(self, params):
        self.check_disk_space()

        params["token"] = self.token

        url = "{host}/system/sync?p=get_stat".format(host = self.host)
        result = netutil.http_get(url, params = params)
        result_obj = textutil.parse_json(result, ignore_error = True)
        return result_obj    

    def list_files(self, offset):
        url = "{host}/system/sync?p=list_files&token={token}&offset={offset}".format(
            host = self.host, token = self.token, offset = offset)

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
        print_debug_info("磁盘剩余容量:", fsutil.format_size(free_space))
        return free_space >= 1024 ** 3 # 要大于1G

    def download_file(self, item):
        if self.admin_token is None:
            print_debug_info("admin_token为空，跳过")
            return

        if not self.check_disk_space():
            print_debug_info("磁盘容量不足，跳过")
            return

        # TODO 检查磁盘容量

        fpath = item.fpath
        web_path = item.web_path
        mtime = item.mtime

        encoded_fpath = xutils.urlsafe_b64encode(fpath)
        url = "{host}/fs_download".format(host = self.host)
        params = dict(token = self.admin_token, fpath = encoded_fpath)
        url = netutil._join_url_and_params(url, params)

        data_dir  = xconfig.get_system_dir("data")
        temp_path = fsutil.get_relative_path(web_path, "/data/")
        dest_path = os.path.join(data_dir, temp_path)
        dirname   = os.path.dirname(dest_path)

        if self.is_same_file(dest_path, item):
            print_debug_info("文件没有变化，跳过")
            return

        fsutil.makedirs(dirname)

        print_debug_info("原始文件:", url)
        print_debug_info("目标文件:", dest_path)

        netutil.http_download(url, dest_path)
        os.utime(dest_path, times=(mtime, mtime))

    def download_files(self, result):
        for item in result.data:
            self.download_file(Storage(**item))

xutils.register_func("system_sync.HttpClient", HttpClient)

