# encoding=utf-8
import zipfile
import os
import re
import time

import web
import xconfig
import xtemplate
import xutils
from util import dateutil
from util import fsutil

html = """{% extends base.html %}

{% block body %}
    <h2>备份管理</h2>
    <table class="table">
        <tr>
            <th>备份名称</th>
            <th>备份路径</th>
            <th>备份时间</th>
            <th>备份大小</th>
            <th>操作</th>
        <tr>
        {% for info in infolist %}
        <tr>
            <td><a href="/fs/{{info.path}}">{{info.name}}</a></td>
            <td>{{info.path}}</td>
            <td>{{info.mtime}}</td>
            <td>{{info.size}}</td>
            <td><a href="/system/backup_info?op={{info.op}}">备份</a></td>
        </tr>
        {% end %}
    </table>
{% end %}
"""

_black_list = [".zip", ".pyc", ".pdf", "__pycache__", ".git"]

_dirname = "./"

ZIPNAME = "xnote.zip"

_dest_path = os.path.join("static", ZIPNAME)

_MAX_BACKUP_COUNT = 10

def zip_xnote(nameblacklist = [ZIPNAME]):
    dirname = _dirname
    # 创建目标文件
    fp = open(_dest_path, "w")
    fp.close()
    zf = zipfile.ZipFile(_dest_path, "w")
    for root, dirs, files in os.walk(dirname):
        for fname in files:
            rootname = os.path.basename(root)
            if rootname in nameblacklist:
                continue
            if fname in nameblacklist:
                continue
            name, ext = os.path.splitext(fname)
            if ext in nameblacklist:
                continue
            path = os.path.join(root, fname)
            try:
                st = os.stat(path)
                if st.st_size > xconfig.MAX_FILE_SIZE:
                    continue
            except:
                continue
            arcname = path[len(dirname):]
            zf.write(path, arcname)
    zf.close()

def zip_new_xnote():
    zip_xnote([ZIPNAME, "data.db", "log", "backup", ".exe",
        "02", "01", "09", "10", "11", "12"])


class FileInfo:

    def __init__(self, name, path, op):
        self.name = name
        self.path = path
        self.op   = op
        info = self

        if os.path.exists(path):
            info.path = path
            st = os.stat(path)
            info.mtime = dateutil.format_time(st.st_mtime)
            info.size = fsutil.format_size(st.st_size)
        else:
            info.path = None
            info.mtime = None
            info.size = None

def backup_code():
    # zip_new_xnote()
    dirname = "./"
    dest_path = xconfig.CODE_ZIP
    xutils.zip_dir(dirname, dest_path, excluded=["data", "tmp", "log", ".git"])

def backup_data():
    dirname = xconfig.DATA_DIR
    dest_path = os.path.join(dirname, "data.zip")
    xutils.zip_dir(dirname, dest_path, excluded=["data.db", "code.zip",
        "dictionary.db", "app", "backup", "tmp", "log"])


class handler:
    def GET(self):
        op = web.input(op=None).op
        if op == "backup":
            zip_xnote()
        elif op == "backup_code":
            backup_code()
        elif op == "backup_data":
            backup_data()
        else:
            infolist = []
            infolist.append(FileInfo("代码", xconfig.CODE_ZIP, "backup_code"))
            infolist.append(FileInfo("数据", xconfig.DATA_ZIP, "backup_data"))
            return xtemplate.render_text(html, infolist=infolist)
        raise web.seeother("/system/backup_info")
