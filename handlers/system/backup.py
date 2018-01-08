# encoding=utf-8
"""
备份相关，需要添加到定时任务中，参考system/crontab
"""
import zipfile
import os
import re
import time
import xutils
import xconfig
from xutils import Storage
from util import dateutil
from util import fsutil
from util import logutil

config = xconfig

_black_list = [".zip", ".pyc", ".pdf", "__pycache__", ".git"]
_dirname = "./"
_zipname = "xnote.zip"
_dest_path = os.path.join(_dirname, "static", _zipname)

# 是否移除旧备份
_remove_old = False
_MAX_BACKUP_COUNT = 10
# 10天备份一次
_BACKUP_INTERVAL = 10 * 3600 * 24

def zip_xnote(nameblacklist = [_zipname]):
    dirname = "./"
    fp = open(_dest_path, "w")
    fp.close()
    zf = zipfile.ZipFile(_dest_path, "w")
    for root, dirs, files in os.walk(dirname):
        for fname in files:
            if fname in nameblacklist:
                continue
            name, ext = os.path.splitext(fname)
            if ext in _black_list or fname in nameblacklist:
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
    zip_xnote([_zipname, ".db", ".log", ".exe"])

def get_info():
    info = Storage()
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


def backup_db():
    now = time.strftime("%Y%m%d")
    dbname = "data.{}.db".format(now)
    dbpath = config.get("DB_PATH")
    if not os.path.exists(dbpath):
        return
    backup_dir = config.get("BACKUP_DIR")
    newdbpath = os.path.join(backup_dir, dbname)
    fsutil.copy(dbpath, newdbpath)

def chk_backup():
    backup_dir = config.get("BACKUP_DIR")
    xutils.makedirs(backup_dir)
    files = os.listdir(backup_dir)
    sorted_files = sorted(files)
    logutil.info("sorted backup files: {}", sorted_files)
    if _remove_old and len(sorted_files) > _MAX_BACKUP_COUNT:
        target = sorted_files[0]
        target_path = os.path.join(backup_dir, target)
        fsutil.remove(target_path)
        logutil.warn("remove file {}", target_path)
    if len(sorted_files) == 0:
        backup_db()
    else:
        lastfile = sorted_files[-1]
        p = re.compile(r"data\.(\d+)\.db")
        m = p.match(lastfile)
        if m:
            data = m.groups()[0]
            tm_time = time.strptime(data, "%Y%m%d")
            seconds = time.mktime(tm_time)
            now = time.time()
            # backup every 10 days.
            if now - seconds > _BACKUP_INTERVAL:
                backup_db()
        else:
            # 先创建一个再删除
            backup_db()
            lastfile_path = os.path.join(backup_dir, lastfile)
            fsutil.remove(lastfile_path)
            logutil.warn("not valid db backup file, remove {}", lastfile_path)

class handler:
    """触发备份事件"""
    def GET(self):
        chk_backup()
        return "OK"
    
# chk_backup()

