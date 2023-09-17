# -*- coding:utf-8 -*-
# @author xupingmao <578749341@qq.com>
# @since 2019/06/28 01:01:33
# @modified 2022/04/04 14:07:12
import os
import time
import xutils
import xconfig
import xauth
import handlers.note.dao as note_dao
import handlers.note.dao_delete as dao_delete
from xutils import dateutil
from xutils.db.binlog import BinLog

MAX_DEPTH = 3
NOTE_DAO  = xutils.DAO("note")

def is_empty_dir(dirname):
    return len(os.listdir(dirname)) == 0

def is_system_dir(dirname):
    return dirname in xconfig.get_system_files()

def rm_expired_files(dirname, expired_time, depth=0, hard=False):
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
        fpath = os.path.abspath(fpath)
        if os.path.islink(fpath):
            xutils.info("DiskClean", "%s is a link" % fname)
            continue
        if os.path.isdir(fpath):
            rm_expired_files(fpath, expired_time, depth+1, hard=hard)
            if is_empty_dir(fpath) and not is_system_dir(fpath):
                xutils.rmfile(fpath)
        else:
            st = os.stat(fpath)
            if now - st.st_ctime >= expired_time:
                xutils.info("DiskClean", "%s is expired" % fname)
                xutils.rmfile(fpath, hard=hard)

def rm_expired_notes(expired_time):
    for user_info in xauth.iter_user(limit = -1):
        user_name = user_info.name
        notes = note_dao.list_removed(user_name, offset = 0, limit = 20, orderby = "dtime_asc")
        for note in notes:
            print("id:{note.id},dtime:{note.dtime},name:{note.name}".format(note = note))

            now = time.time()
            delete_timestamp = dateutil.parse_time(note.dtime)

            # 处理脏数据
            note_full = note_dao.get_by_id(note.id)
            if note_full is None:
                print("delete dirty note, id:{note.id}, name:{note.name}".format(note = note))
                dao_delete.delete_note_physically(note.creator, note.id)

            if now - delete_timestamp >= expired_time:
                dao_delete.delete_note(note.id)
                print("note expired, id:{note.id},name:{note.name}".format(note = note))

def rm_expired_binlog():
    binlog = BinLog.get_instance()
    binlog.delete_expired()

class handler:

    @xauth.login_required("admin")
    def GET(self):
        # 数据库备份文件
        db_expire_seconds = xconfig.FileConfig.db_backup_expire_days * dateutil.SECONDS_PER_DAY
        rm_expired_files(xconfig.BACKUP_DIR, db_expire_seconds, hard=True)
        
        # 日志文件
        rm_expired_files(xconfig.LOG_DIR, xconfig.LOG_EXPIRE, hard=True)

        # 回收站和临时文件
        rm_expired_files(xconfig.TRASH_DIR, xconfig.TRASH_EXPIRE)
        rm_expired_files(xconfig.TMP_DIR, xconfig.TMP_EXPIRE, hard=True)

        # 删除回收站过期的笔记
        rm_expired_notes(xconfig.NOTE_REMOVED_EXPIRE)

        # 删除过期的binlog
        rm_expired_binlog()

        return "success"

xurls = (
    r"/cron/diskclean", handler
)