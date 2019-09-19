# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/06/28 01:01:33
# @modified 2019/09/18 00:10:27
import zipfile
import os
import re
import time
import xutils
import xconfig
import xauth
from xutils import Storage
from xutils import dateutil, fsutil, logutil

MAX_DEPTH = 3

def is_empty_dir(dirname):
    return len(os.listdir(dirname)) == 0

def rm_expired_files(dirname, expired_time, depth=0):
    if depth > MAX_DEPTH:
        xutils.error("DiskClean", "too deep path, dirname: %s" % dirname)
        return
    xutils.info("DiskClean", "check dirname `%s`" % dirname)
    now = time.time()
    for fname in os.listdir(dirname):
        fpath = os.path.join(dirname, fname)
        if os.path.islink(fpath):
            continue
        if os.path.isdir(fpath):
            rm_expired_files(fpath, expired_time, depth+1)
            if is_empty_dir(fpath):
                xutils.rmfile(fpath)
        st = os.stat(fpath)
        if now - st.st_ctime >= expired_time:
            xutils.info("DiskClean", "%s is expired" % fname)
            xutils.rmfile(fpath)

class handler:

    @xauth.login_required("admin")
    def GET(self):
        rm_expired_files(xconfig.BACKUP_DIR, xconfig.BACKUP_EXPIRE)
        rm_expired_files(xconfig.LOG_DIR, xconfig.LOG_EXPIRE)
        rm_expired_files(xconfig.TRASH_DIR, xconfig.TRASH_EXPIRE)
        rm_expired_files(xconfig.TMP_DIR, xconfig.TMP_EXPIRE)

xurls = (
    r"/cron/diskclean", handler
)