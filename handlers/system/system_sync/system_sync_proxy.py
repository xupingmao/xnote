# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2021/11/29 22:48:26
@LastEditors  : xupingmao
@LastEditTime : 2023-08-26 01:49:50
@FilePath     : /xnote/handlers/system/system_sync/system_sync_proxy.py
@Description  : 网络代理
"""

import os
import time
import logging

import xutils
import xconfig

from xutils import Storage
from xutils import netutil
from xutils import textutil
from xutils import dateutil
from xutils import fsutil
from xutils import dbutil
from xutils.six.moves.urllib.parse import quote
from xutils.mem_util import log_mem_info_deco
from .models import FileIndexInfo
from .system_sync_indexer import build_index_by_fpath

RETRY_INTERVAL = 60
MAX_KEY_SIZE = 511

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
        self.debug = True

    def get_table(self):
        return dbutil.get_hash_table("fs_sync_index_copy")

    def get_failed_table(self):
        return dbutil.get_table("fs_sync_index_failed")

    def delete_retry_task(self, item):
        db = self.get_failed_table()
        result = db.list(filter_func = lambda k,x:x.webpath==item.webpath)
        for result_item in result:
            db.delete(result_item)
    
    def upsert_retry_task(self, item):
        db = self.get_failed_table()
        first = db.get_first(filter_func=lambda k,x:x.webpath==item.webpath)
        if first == None:
            db.insert(item)
        else:
            db.update_by_key(first._key, item)

    def check_failed(self):
        if self.host is None:
            logging.warning("host为空")
            return True

        return False

    def get_stat(self, params):
        self.check_disk_space()
        if self.check_failed():
            return

        params["token"] = self.token

        url = "{host}/system/sync/leader?p=get_stat".format(host = self.host)
        result = netutil.http_get(url, params = params, skip_empty_value = True)
        result_obj = textutil.parse_json(result, ignore_error = True)
        return result_obj    

    def list_files(self, last_id=0):
        if self.check_failed():
            return

        last_id_str = str(last_id)
        url = "{host}/system/sync/leader?p=list_files&token={token}&last_id={last_id}".format(
            host = self.host, token = self.token, last_id = last_id_str)
        
        if self.debug:
            logging.info("sync_from_leader: %s", url)

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

    def download_file(self, item: FileIndexInfo):
        if self.admin_token is None:
            logging.warn("admin_token为空，跳过")
            return

        if not self.check_disk_space():
            logging.error("磁盘容量不足，跳过")
            raise Exception("磁盘容量不足")
        
        if item.ftype == "dir":
            logging.info("跳过目录, dir=%s", item.fpath)
            return

        fpath = item.fpath
        web_path = item.web_path
        try:
            mtime = dateutil.parse_datetime(item.mtime)
        except:
            mtime = time.time()
        
        # 先保存失败记录，成功后再删除
        self.upsert_retry_task(item)

        try:
            # 文件名太长会导致保存失败
            # 保存文件索引信息
            table = self.get_table()
            item.last_try_time = time.time()
            table.put(web_path, item)
        except:
            item.err_msg = xutils.print_exc()
            self.upsert_retry_task(item)

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
            self.delete_retry_task(item)
            return

        fsutil.makedirs(dirname)

        logging.debug("原始文件:%s", url)
        logging.debug("目标文件:%s", dest_path)

        try:
            netutil.http_download(url, dest_path)
            os.utime(dest_path, times=(mtime, mtime))
            self.delete_retry_task(item)
            build_index_by_fpath(dest_path)
        except:
            item.err_msg = xutils.print_exc()
            self.upsert_retry_task(item)
            logging.error("下载文件失败:%s", dest_path)

    def download_files(self, result):
        for item in result.data:
            self.download_file(FileIndexInfo(**item))

    def retry_failed(self):
        """TODO 这个应该是调度层的"""
        for item in self.get_failed_table().iter(limit = -1):
            now = time.time()
            if item.last_try_time is not None and (now - item.last_try_time) > RETRY_INTERVAL:
                continue

            logging.debug("正在重试:%s", item)
            self.download_file(item)

    @log_mem_info_deco("proxy.http_get")
    def http_get(self, url, params=None):
        return netutil.http_get(url, params=params)

    @log_mem_info_deco("proxy.list_binlog")
    def list_binlog(self, last_seq=0) -> dict:
        assert isinstance(last_seq, int)
        params = dict(last_seq=str(last_seq), include_req_seq="false")

        leader_host = self.host
        leader_token = self.token
        url = "{host}/system/sync/leader?p=list_binlog&token={token}".format(
            host=leader_host, token=leader_token)
        
        result = self.http_get(url, params=params)
        try:
            result_obj = textutil.parse_json(result)
            assert isinstance(result_obj, dict)
            return result_obj
        except:
            logging.error("解析json失败, result=%s", result)
            raise Exception("解析JSON失败")
    
    def list_db(self, last_key):
        # type: (str) -> str
        leader_token = self.token
        leader_host = self.host
        params = dict(last_key=last_key, token=leader_token)
        url = "{host}/system/sync/leader?p=list_db".format(host=leader_host)
        return netutil.http_get(url, params=params)


empty_http_client = HttpClient("", "", "")
