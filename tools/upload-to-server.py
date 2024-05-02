# -*- coding:utf-8 -*-
"""
@Author       : xupingmao
@email        : 578749341@qq.com
@Date         : 2024-05-01 20:48:16
@LastEditors  : xupingmao
@LastEditTime : 2024-05-02 20:59:13
@FilePath     : /xnote/tools/upload-to-server.py
@Description  : 上传文件到服务器
"""

import os
import xutils
import fire
import requests
import sys

from xnote.core import xtables
from xutils import jsonutil
from xutils import dateutil

class Uploader:

    upload_server = "http://server:port"
    upload_path = "/fs_upload"
    upload_token = "your_token"

    def init_db(self):
        table_name = "upload_record"
        dbpath = "upload_record.db"
        with xtables.create_table_manager_with_dbpath(table_name, dbpath=dbpath) as manager:
            manager.add_column("create_time", "datetime", default_value=xtables.DEFAULT_DATETIME, comment="创建时间")
            manager.add_column("update_time", "datetime", default_value=xtables.DEFAULT_DATETIME, comment="更新时间")
            manager.add_column("remote_file", "varchar(1024)", default_value="", comment="远程文件路径")
            manager.add_index("remote_file")

    def __init__(self):
        self.init_db()
        self.db = xtables.get_table_by_name("upload_record")
        config = xutils.load_json_config("./upload.config.json")
        self.upload_domain = config.get("upload_server")
        self.upload_token = config.get("upload_token")
        assert self.upload_domain != None
        assert self.upload_token != None

    def get_target_file(self, fpath="", dirname="", target_dirname=""):
        relative_path = xutils.get_relative_path(fpath, parent=dirname)
        result = os.path.join(target_dirname, relative_path)
        return result.replace("\\", "/")

    def upload_dir(self, dirname="", target_dirname=""):
        if dirname == "":
            raise Exception("dirname不能为空")
        if target_dirname == "":
            raise Exception("target_dirname不能为空")
        if not os.path.exists(dirname):
            raise Exception(f"文件夹不存在: {dirname}")
        
        for root, dirs, files in os.walk(dirname):
            for fname in files:
                fpath = os.path.join(root, fname)
                target_file = self.get_target_file(fpath, dirname, target_dirname)
                print(f"upload {fpath} to {target_file}")
                self.do_upload(fpath, target_file)
    
    def do_upload(self, fpath="", target_file=""):
        record = self.db.select_first(where=dict(remote_file=target_file))
        if record != None:
            print(r"file already uploaded, fpath={fpath}, target_file={target_file}")
            return
        
        with open(fpath, "rb+") as fp:
            files = {"file": (target_file, fp, "application/json")}
            
            params = dict(token=self.upload_token, upload_type="recovery")
            upload_url = self.upload_domain + self.upload_path
            print(f"starting to upload {fpath} to {target_file}")
            res = requests.post(upload_url, params=params, files=files)

            print("result:", res.text)
            result_obj = xutils.parse_json(res.text)
            assert isinstance(result_obj, dict)
            result_code = result_obj.get("code")
            if result_code != "success":
                print("upload failed")
                sys.exit(1)
            else:
                now = dateutil.format_datetime()
                self.db.insert(create_time=now, update_time=now, remote_file=target_file)

if __name__ == "__main__":
    uploader = Uploader()
    fire.Fire(uploader.upload_dir)
