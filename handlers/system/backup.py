# encoding=utf-8
# @author xupingmao
# @since 2017/07/29
# @modified 2022/03/31 12:33:26
"""备份相关，系统默认会添加到定时任务中，参考system/crontab
"""
import zipfile
import os
import time
import sys
import logging
import threading
import sqlite3

import xutils
from xnote.core import xconfig, xauth, xtemplate
import web.db

from xutils import Storage
from xutils import dbutil
from xutils import fsutil, logutil
from xutils.db.driver_sqlite import SqliteKV
from xnote.core import xtables
from xnote.service import JobService, SysJob, JobStatusEnum

config = xconfig

_black_list = [".zip", ".pyc", ".pdf", "__pycache__", ".git"]
_dirname = "./"
_zipname = "xnote.zip"
_dest_path = os.path.join(_dirname, "static", _zipname)

# 删除备份在 cron/diskclean 任务里面
# 备份的锁
_backup_lock = threading.RLock()
_import_logger = logutil.new_mem_logger("import_db", size = 20)

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


def chk_scripts_backup():
    dirname = xconfig.SCRIPTS_DIR
    destfile = os.path.join(xconfig.BACKUP_DIR, time.strftime("scripts.%Y-%m-%d.zip"))
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

        # TODO 删除多余的备份文件
    
    def get_backup_logger(self):
        return logutil.get_mem_logger("backup_db", size = 20, ttl = -1)

    def dump_db(self, backup_kv = True, backup_sql=True):
        count = 0
        if backup_kv:
            count = self.backup_kv_store()
        if backup_sql:
            self.backup_sql_tables()
        return count
    
    def backup_sql_tables(self):
        logger = self.get_backup_logger()
        db = xtables.MySqliteDB(db = self.db_backup_file)
        # 备份可以关闭同步，加快速度
        db.query("PRAGMA synchronous = OFF")
        db.query("PRAGMA journal_mode = WAL")
        db.query("PRAGMA page_size = 16384") # 16K
        batch_size = 100

        try:
            for table in xtables.get_all_tables():
                backup_table = xtables.init_backup_table(table.tablename, db)
                backup_table.writable = True
                backup_table.log_profile = False # 备份的时候不需要profile
                
                total_count = table.count()
                logger.info("backup table:(%s) count:(%d)", table.tablename, total_count)
                start_time = time.time()
                count = 0
                for records in table.iter_batch(batch_size=batch_size):
                    batch = []
                    for record in records:
                        new_record = table.filter_record(record)
                        batch.append(new_record)
                        count += 1
                    # 只更新结构包含的字段
                    self.multiple_insert(backup_table, batch)
                    batch = []
                    cost_time = time.time() - start_time
                    qps = calc_qps(count, cost_time)
                    logger.log("table:(%s), proceed:(%d/%d), qps:(%.2f)" % (backup_table.tablename, count, total_count, qps))
                cost_time = time.time() - start_time
                logger.info("backup table:(%s) done! cost_time:(%.2fs)", table.tablename, cost_time)
        except:
            err_info = xutils.print_exc()
            logger.info("backup failed: (%s)" % err_info)
        finally:
            db.ctx.db.close()
            del db

    def multiple_insert(self, db, batch):
        with db.transaction():
            for value in batch:
                db.insert(**value)

    def backup_kv_store(self):
        logger = self.get_backup_logger()

        total_count = dbutil.count_all()
        start_time = time.time()

        DBBackup._start_time = time.time()
        DBBackup._total = total_count

        db2 = SqliteKV(self.db_backup_file, debug = False)
        count = 0
        try:
            batch = dbutil.create_write_batch()
            for key, value in dbutil.get_instance().RangeIter(include_value = True):
                # 可能是bytearray
                key = bytes(key)
                value = bytes(value)
                
                if key.startswith(b"_index$"):
                    # 索引不需要备份
                    continue

                batch.put_bytes(key, value)
                count += 1
                # 更新进度
                DBBackup._progress = count / total_count
                if count % 100 == 0:
                    db2.Write(batch)
                    batch = dbutil.create_write_batch()

                    cost_time = time.time() - start_time
                    progress = count/total_count*100.0
                    qps = calc_qps(count, cost_time)
                    logger.log("proceed:(%d), progress:(%.2f%%), qps:(%.2f)" % (count, progress, qps))

            db2.Write(batch)
            db2.Close()

            logger.log("backup done, total:(%d), cost_time:(%.2fs)", count, time.time()-start_time)
        except:            
            stack_info = xutils.print_exc()
            logger.log("backup failed, err:%s", stack_info)
        finally:
            db2 = None
            DBBackup._start_time = -1
            DBBackup._count = -1
            DBBackup._progress = 0.0
        return count


    def execute(self, backup_kv=True):
        logger = self.get_backup_logger()
        got_lock = False
        try:
            if _backup_lock.acquire(blocking = False):
                got_lock = True
                self.do_execute(backup_kv=backup_kv)
            else:
                logger.log("backup is busy")
                return "backup is busy"
        finally:
            if got_lock:
                _backup_lock.release()

    def do_execute(self, backup_kv=True):
        
        job_info = SysJob()
        job_info.job_type = "db_backup"
        
        with JobService.run_with_job(job_info):
            # 先做清理工作
            self.clean()

            start_time = time.time()
            # 执行备份
            count = self.dump_db(backup_kv=backup_kv)

            cost_time = (time.time() - start_time) * 1000.0
            logging.info("数据库记录总数:%s", count)

            # 保存为压缩文件
            dirname = os.path.join(xconfig.BACKUP_DIR, "db")
            xutils.makedirs(dirname)
            
            destfile = os.path.join(dirname, time.strftime("%Y-%m-%d.db"))

            if os.path.exists(destfile):
                fsutil.rmfile(destfile)

            fsutil.mvfile(self.db_backup_file, destfile)

            # 再次清理
            self.clean()
            
            job_info.job_status = JobStatusEnum.success
            job_info.job_result = "备份任务完成"

            return dict(count = count, cost_time = "%sms" % cost_time)

def chk_db_backup():
    if not xconfig.get_system_config("db_backup"):
        return
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


class DBImporter:

    def import_db(self, db_file):
        self.db_backup_file = db_file
        got_lock = False
        try:
            if _backup_lock.acquire(blocking = False):
                got_lock = True
                self.import_sql(db_file)
                return self.import_kv(db_file)
            else:
                logging.warning("import_db is busy")
                return "import_db is busy"
        except:
            exc_info = xutils.print_exc()
            _import_logger.info(exc_info)
        finally:
            if got_lock:
                _backup_lock.release()

    def get_logger(self):
        return _import_logger

    def import_sql(self, db_file):
        logger = self.get_logger()
        backup_db = xtables.MySqliteDB(db = db_file)
        batch_size = 100

        try:
            for table in xtables.get_all_tables():
                backup_table = xtables.init_backup_table(table.tablename, backup_db)
                total_count = backup_table.count()
                logger.info("import table:(%s) count:(%d)", table.tablename, total_count)
                start_time = time.time()
                count = 0
                assert isinstance(table, xtables.TableProxy)
                for records in backup_table.iter_batch(batch_size=batch_size):
                    with table.transaction():
                        for record in records:
                            new_record = table.filter_record(record)
                            where_dict = dict(id = record.id)
                            old_record = table.select_first(where=where_dict)
                            if old_record == None:
                                table.insert(**new_record)
                            else:
                                table.update(where=where_dict, **new_record)
                            count+=1
                            cost_time = time.time() - start_time
                            qps = calc_qps(count, cost_time)
                        logger.log("table:(%s), proceed:(%d/%d), qps:(%.2f)" % (backup_table.tablename, count, total_count, qps))
                cost_time = time.time() - start_time
                logger.info("import table:(%s) done! cost_time:(%.2fs)", table.tablename, cost_time)
        except Exception as e:
            err_info = xutils.print_exc()
            logger.info("import failed: (%s)" % err_info)
            raise e

    def import_kv(self, db_file):
        count = 0
        logger = _import_logger
        db = sqlite3.connect(db_file)
        total_count = list(db.execute("SELECT COUNT(1) FROM kv_store"))[0][0]

        if total_count == 0:
            logger.log("db is empty")
            return

        sql = "SELECT key, value FROM kv_store ORDER BY key"

        start_time = time.time()
        batch_size = 100

        write_batch = dbutil.create_write_batch()
        for key, value in db.execute(sql):
            write_batch.put_bytes(key, value)
            count += 1
            if count % batch_size == 0:
                write_batch.commit(retries=5)
                write_batch = dbutil.create_write_batch()
                cost_time = time.time() - start_time
                progress = count/total_count*100.0
                qps = calc_qps(count, cost_time)
                logger.log("proceed:(%d), progress:(%.2f%%), qps:(%.2f)" % (count, progress, qps))

        write_batch.commit(retries=5)

        logger.log("import record done records:%s", count)
        for table_name in dbutil.get_table_names():
            logger.log("repair index for (%s)", table_name)
            try:
                dbutil.get_table(table_name).repair_index()
                logger.log("repair index done for (%s)", table_name)
            except:
                xutils.print_exc()
                logger.log("repair index failed for (%s)", table_name)

        logger.log("import done!")
        return "records:%s" % count



def import_db(db_file):
    importer = DBImporter()
    return importer.import_db(db_file)

class BackupHandler:

    @xauth.login_required("admin")
    def GET(self):
        """触发备份事件"""
        p = xutils.get_argument("p", "")

        if p == "db_backup_home":
            return xtemplate.render("system/page/db/db_backup.html", 
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

        if p == "backup_sql":
            backup = DBBackup()
            backup.execute(backup_kv=False)
            return "backup_sql"

        # 备份所有的
        chk_db_backup()
        chk_scripts_backup()
        return "OK"
    
# chk_backup()

xurls = (
    r"/system/backup", BackupHandler,
)
