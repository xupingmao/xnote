# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/06/28 01:01:33
# @modified 2021/08/07 19:08:21
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
NOTE_DAO  = xutils.DAO("note")

def is_empty_dir(dirname):
    return len(os.listdir(dirname)) == 0

def rm_expired_files(dirname, expired_time, depth=0):
    if not os.path.exists(dirname):
        xutils.error("DiskClean", "dirname `%s` not eixsts" % dirname)
        return
    if depth > MAX_DEPTH:
        xutils.error("DiskClean", "too deep path, dirname: %s" % dirname)
        return
    xutils.info("DiskClean", "check dirname `%s`" % dirname)
    now = time.time()
    for fname in os.listdir(dirname):
        fpath = os.path.join(dirname, fname)
        if os.path.islink(fpath):
            xutils.info("DiskClean", "%s is a link" % fname)
            continue
        if os.path.isdir(fpath):
            rm_expired_files(fpath, expired_time, depth+1)
            if is_empty_dir(fpath):
                xutils.rmfile(fpath)
        else:
            st = os.stat(fpath)
            if now - st.st_ctime >= expired_time:
                xutils.info("DiskClean", "%s is expired" % fname)
                xutils.rmfile(fpath)

def rm_expired_notes(expired_time):
    for user_name in xauth.list_user_names():
        notes = NOTE_DAO.list_removed(user_name, offset = 0, limit = 20, orderby = "dtime_asc")
        for note in notes:
            print("id:{note.id},dtime:{note.dtime},name:{note.name}".format(note = note))

            now = time.time()
            delete_timestamp = dateutil.parse_time(note.dtime)

            # 处理脏数据
            note_full = NOTE_DAO.get_by_id(note.id)
            if note_full is None:
                print("delete dirty note, id:{note.id}, name:{note.name}".format(note = note))
                NOTE_DAO.delete_physically(note.creator, note.id)

            if now - delete_timestamp >= expired_time:
                NOTE_DAO.delete(note.id)
                print("note expired, id:{note.id},name:{note.name}".format(note = note))

class handler:

    @xauth.login_required("admin")
    def GET(self):
        rm_expired_files(xconfig.BACKUP_DIR, xconfig.BACKUP_EXPIRE)
        rm_expired_files(xconfig.LOG_DIR, xconfig.LOG_EXPIRE)
        rm_expired_files(xconfig.TRASH_DIR, xconfig.TRASH_EXPIRE)
        rm_expired_files(xconfig.TMP_DIR, xconfig.TMP_EXPIRE)

        # 删除回收站过期的笔记
        rm_expired_notes(xconfig.NOTE_REMOVED_EXPIRE)

xurls = (
    r"/cron/diskclean", handler
)