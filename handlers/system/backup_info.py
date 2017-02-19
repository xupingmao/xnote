# encoding=utf-8
import xtemplate
import web

html = """{% extends base.html %}

{% block body %}
    <p>路径 {{info.path}} </p>
    <p>备份时间 {{info.mtime}}</p>
    <p>大小 {{info.size}}</p>
    <p> <a href="/static/xnote.zip">下载</a>
    <p><a href="/system/backup_info?op=backup">重新备份</a></p>
    <p><a href="/system/backup_info?op=backup_code">只备份代码</a></p>
{% end %}
"""

import zipfile
import os
from util import dateutil
from util import fsutil
from util import logutil
import config
import re
import time

import xutils

class T:
    pass

_black_list = [".zip", ".pyc", ".pdf", "__pycache__", ".git"]

_dirname = "./"

_zipname = "xnote.zip"

_dest_path = os.path.join("static", _zipname)

_MAX_BACKUP_COUNT = 10

def zip_xnote(nameblacklist = [_zipname]):
    dirname = _dirname
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
                if st.st_size > config.MAX_FILE_SIZE:
                    continue
            except:
                continue
            arcname = path[len(dirname):]
            zf.write(path, arcname)
    zf.close()

def zip_new_xnote():
    zip_xnote([_zipname, "data.db", "log", "backup", ".exe", 
        "02", "01", "09", "10", "11", "12"])

def get_info():
    info = T()
    info.path = _dest_path

    if os.path.exists(_dest_path):
        info.name = _zipname
        info.path = _dest_path
        st = os.stat(_dest_path)
        info.mtime = dateutil.format_time(st.st_mtime)
        info.size = fsutil.format_size(st.st_size)
    else:
        info.name = None
        info.path = None
        info.mtime = None
        info.size = None
    return info

def backup_code():
    zip_new_xnote()

class handler:

    def GET(self):
        op = web.input(op=None).op
        if op == "backup":
            zip_xnote()
        elif op == "backup_code":
            backup_code()
        return xtemplate.render_text(html, info = get_info())