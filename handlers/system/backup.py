# encoding=utf-8
# @author xupingmao
# @since 2017/07/29
# @modified 2022/03/19 17:55:28
"""备份相关，系统默认会添加到定时任务中，参考system/crontab
"""
import zipfile
import os
import re
import time
import sys
import logging
import threading
import sqlite3

import xutils
import xconfig
import xauth
import xtemplate
from xutils import Storage
from xutils import dbutil
from xutils import dateutil, fsutil, logutil
from xutils.db.driver_sqlite import SqliteKV

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

# 备份的锁
_backup_lock = threading.RLock()

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
                if st.st_size > xconfig.MAX_FILE_SIZE:
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
    dbpath = xconfig.DB_FILE
    if not os.path.exists(dbpath):
        return
    backup_dir = xconfig.BACKUP_DIR
    newdbpath = os.path.join(backup_dir, dbname)
    fsutil.copy(dbpath, newdbpath)

def chk_backup():
    backup_dir = xconfig.BACKUP_DIR
    xutils.makedirs(backup_dir)
    files = os.listdir(backup_dir)
    sorted_files = sorted(files)
    logutil.info("sorted backup files: {}", sorted_files)

    for fname in sorted_files:
        path = os.path.join(backup_dir, fname)
        ctime = os.stat(path).st_ctime
        print("%s - %s" % (path, xutils.format_time(ctime)))

    tm = time.localtime()
    if tm.tm_wday != 5:
        print("not the day, quit")
        # 一周备份一次
        return

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


def chk_scripts_backup():
    dirname = xconfig.SCRIPTS_DIR
    destfile = os.path.join(xconfig.BACKUP_DIR, time.strftime("scripts.%Y-%m.zip"))
    xutils.zip_dir(dirname, destfile)

class DBBackup:
    """数据库备份"""

    _progress = 0.0
    _start_time = -1
    _total = 0

    def __init__(self):
        self.db_backup_file = os.path.join(xconfig.TMP_DIR, "temp.db")

    @staticmethod
    def progress():
        return "%.2f%%" % (DBBackup._progress * 100.0)

    @staticmethod
    def run_time():
        start_time = DBBackup._start_time
        if start_time < 0:
            return "-1"

        return "%.2fs" % (time.time() - start_time)

    @staticmethod
    def rest_time():
        progress = DBBackup._progress
        if progress == 0:
            return "-1"

        cost_time = time.time() - DBBackup._start_time
        total_time = cost_time / progress
        rest_time = total_time - cost_time
        return "%.2fs" % rest_time

    @staticmethod
    def total():
        return DBBackup._total

    def clean(self):
        db_backup_file = self.db_backup_file
        if os.path.exists(db_backup_file):
            logging.info("删除db备份文件:%s", db_backup_file)
            fsutil.rmfile(db_backup_file, hard = True)

    def dump_db(self):
        logger = logutil.new_mem_logger("backup_db", size = 20)

        total_count = dbutil.count_all()
        start_time = time.time()

        DBBackup._start_time = time.time()
        DBBackup._total = total_count

        db2 = SqliteKV(self.db_backup_file, debug = False)
        count = 0
        try:
            for key, value in dbutil.get_instance().RangeIter(include_value = True):
                db2.Put(key, value)
                count += 1
                # 更新进度
                DBBackup._progress = count / total_count
                if count % 100 == 0:
                    cost_time = time.time() - start_time
                    progress = count/total_count*100.0
                    qps = calc_qps(count, cost_time)
                    logger.log("proceed:(%d), progress:(%.2f%%), qps:(%.2f)" % (count, progress, qps))
            db2.Close()

            logger.log("backup done, total:(%d), cost_time:(%.2fs)", count, time.time()-start_time)
        finally:
            db2 = None
            DBBackup._start_time = -1
            DBBackup._count = -1
            DBBackup._progress = 0.0
        return count

    def execute(self):
        try:
            got_lock = False
            if _backup_lock.acquire(blocking = False):
                self.do_execute()
            else:
                logging.warning("backup is busy")
                return "backup is busy"
        finally:
            if got_lock:
                _backup_lock.release()

    def do_execute(self):
        # 先做清理工作
        self.clean()

        start_time = time.time()
        # 执行备份
        count = self.dump_db()

        cost_time = (time.time() - start_time) * 1000.0
        logging.info("数据库记录总数:%s", count)

        # 保存为压缩文件
        dirname = os.path.join(xconfig.BACKUP_DIR, "db")
        xutils.makedirs(dirname)
        
        destfile = os.path.join(dirname, time.strftime("%Y-%m.db"))

        if os.path.exists(destfile):
            fsutil.rmfile(destfile)

        fsutil.mvfile(self.db_backup_file, destfile)

        # 再次清理
        self.clean()

        return dict(count = count, cost_time = "%sms" % cost_time)

def chk_db_backup_old():
    dirname = xconfig.DB_DIR
    destfile = os.path.join(xconfig.BACKUP_DIR, time.strftime("db.%Y-%m.zip"))
    xutils.zip_dir(dirname, destfile)

def chk_db_backup():
    backup = DBBackup()
    return backup.execute()

def calc_key_size():
    count = 0
    key_size = 0
    mem_db = dict()
    for key in dbutil.get_instance().RangeIter(include_value = False):
        key_size += sys.getsizeof(key)
        mem_db[key] = 1
        count += 1
    mem_db_size = sys.getsizeof(mem_db)

    result = Storage()
    result.count = count
    result.mem_db_size = xutils.format_size(sys.getsizeof(mem_db))
    result.key_size = xutils.format_size(key_size)
    result.avg_key_size = xutils.format_size(key_size // count)

    return result

def calc_qps(count, cost_time):
    if cost_time > 0:
        return count/cost_time
    return -1


def import_db(db_file):
    got_lock = False
    try:
        if _backup_lock.acquire(blocking = False):
            got_lock = True
            return _import_db(db_file)
        else:
            logging.warning("import_db is busy")
            return "import_db is busy"
    finally:
        if got_lock:
            _backup_lock.release()

def _import_db(db_file):
    count = 0
    logger = logutil.new_mem_logger("import_db", size = 20)

    db = sqlite3.connect(db_file)
    total_count = list(db.execute("SELECT COUNT(1) FROM kv_store"))[0][0]

    if total_count == 0:
        logger.log("db is empty")
        return

    sql = "SELECT key, value FROM kv_store ORDER BY key"

    db_instance = dbutil.get_instance()
    start_time = time.time()

    for key, value in db.execute(sql):
        db_instance.Put(key, value)
        count += 1
        if count % 100 == 0:
            cost_time = time.time() - start_time
            progress = count/total_count*100.0
            qps = calc_qps(count, cost_time)
            logger.log("proceed:(%d), progress:(%.2f%%), qps:(%.2f)" % (count, progress, qps))
        
    logger.log("[done] records:%s", count)
    return "records:%s" % count

class BackupHandler:

    @xauth.login_required("admin")
    def GET(self):
        """触发备份事件"""
        p = xutils.get_argument("p", "")

        if p == "home":
            return xtemplate.render("system/page/backup.html", 
                total = DBBackup.total(),
                run_time = DBBackup.run_time(),
                rest_time = DBBackup.rest_time(),
                progress = DBBackup.progress())

        if p == "db":
            return chk_db_backup()

        if p == "calc_key_size":
            return calc_key_size()

        if p == "import_db":
            path = xutils.get_argument("path", "")
            return import_db(path)

        # 备份所有的
        chk_backup()
        chk_db_backup()
        chk_scripts_backup()
        return "OK"
    
# chk_backup()

xurls = (
    r"/system/backup", BackupHandler,
)
