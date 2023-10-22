# encoding=utf-8
# @since 2016/12/04
# @modified 2022/04/23 11:07:21
"""xnote - Xnote is Not Only Text Editor
Copyright (C) 2016-2022  xupingmao 578749341@qq.com

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from __future__ import print_function
import argparse
import logging
import time
import sys
import os
from .autoreload import AutoReloadThread
from xutils.db import dbutil_cache
from xutils.lockutil import FileLock
from xutils.mem_util import log_mem_info_deco
from xutils import mem_util
from xutils import Storage
from xutils import dbutil
from xutils import cacheutil, interfaces
from xutils.sqldb import TableProxy
from . import xnote_code_builder
from . import xnote_hooks, xnote_trace, xtables, xtables_kv, xconfig, xtemplate, xmanager, xauth
import threading
import xutils
import web
import atexit

DEFAULT_CONFIG_FILE = xconfig.resolve_config_path("./config/boot/boot.default.properties")

class XnoteApp:

    def __init__(self) -> None:
        self.web_app = web.application()
        self.handler_manager = None # type: None|xmanager.HandlerManager

# 配置日志模块
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s|%(levelname)s|%(filename)s:%(lineno)d|%(message)s')


class XnoteFound(web.Redirect):
    """A `302 Found` redirect."""
    def __init__(self, url, absolute=False):
        url = xconfig.WebConfig.server_home + url
        web.Redirect.__init__(self, url, '302 Found', absolute=absolute)

class XnoteSeeOther(web.Redirect):
    """A `303 See Other` redirect."""
    def __init__(self, url, absolute=False):
        url = xconfig.WebConfig.server_home + url
        web.Redirect.__init__(self, url, '303 See Other', absolute=absolute)

# redirect转换成绝对uri
web.found = XnoteFound
web.seeother = XnoteSeeOther

def get_bool_by_sys_arg(value):
    return value == "yes" or value == "true"


def get_int_by_sys_arg(value):
    if value is None:
        return value
    return int(value)


def handle_args_and_init_config(boot_config_kw=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG_FILE)
    parser.add_argument("--data", default="")
    parser.add_argument("--delay", default="0")
    parser.add_argument("--debug", default="yes")
    parser.add_argument("--minthreads", default="15")
    parser.add_argument("--useCacheSearch", default="no")
    parser.add_argument("--useUrlencode", default="no")
    parser.add_argument("--devMode", default="no")
    parser.add_argument("--initScript", default="init.py")
    parser.add_argument("--test", default="no")

    web.config.debug = False
    args = parser.parse_args()

    if args.data != "":
        logging.error("--data配置已经废弃，请使用--config配置")
        sys.exit(1)

    # 处理Data目录，创建各种目录
    xconfig.init(args.config, boot_config_kw=boot_config_kw)

    # 延迟加载，避免定时任务重复执行
    delay = int(args.delay)
    time.sleep(delay)

    xconfig.MIN_THREADS = xconfig.get_system_config("min_threads")
    xconfig.INIT_SCRIPT = args.initScript
    web.config.minthreads = xconfig.MIN_THREADS

    xconfig.USE_CACHE_SEARCH = get_bool_by_sys_arg(args.useCacheSearch)
    xconfig.USE_URLENCODE = get_bool_by_sys_arg(args.useUrlencode)
    xconfig.IS_TEST = get_bool_by_sys_arg(args.test)

    if xconfig.DEBUG:
        web.config.debug = xconfig.DEBUG

    start_time = xutils.format_datetime()
    xconfig.set_global_config("start_time", start_time)
    xconfig.set_global_config("system.start_time", start_time)


def handle_exit():
    # 优雅下线
    logging.info("准备优雅下线")
    xmanager.fire("sys.exit")


@log_mem_info_deco("init_sql_db")
def init_sql_db():
    # 初始化数据库
    xtables.init()


@log_mem_info_deco("init_kv_engine")
def init_kv_engine():
    try:
        block_cache_size = xconfig.DatabaseConfig.block_cache_size
        write_buffer_size = xconfig.DatabaseConfig.write_buffer_size
        max_open_files = xconfig.DatabaseConfig.max_open_files
        leveldb_kw = dict(block_cache_size=block_cache_size,
                          write_buffer_size=write_buffer_size,
                          max_open_files=max_open_files)

        db_instance = None
        db_driver = xconfig.DatabaseConfig.db_driver_kv

        if db_driver == "sqlite":
            from xutils.db.driver_sqlite import SqliteKV
            db_file = os.path.join(xconfig.DB_DIR, "sqlite", "kv_store.db")
            config_dict = Storage()
            config_dict.sqlite_journal_mode = xconfig.DatabaseConfig.sqlite_journal_mode
            db_instance = SqliteKV(db_file, config_dict=config_dict)
            db_instance.sql_logger = xnote_trace.SqlLogger()
            db_instance.debug = xconfig.DatabaseConfig.db_debug

        if db_driver == "leveldbpy":
            from xutils.db.driver_leveldbpy import LevelDBProxy
            db_instance = LevelDBProxy(xconfig.DB_DIR, **leveldb_kw)

        if db_driver == "lmdb":
            from xutils.db.driver_lmdb import LmdbEnhancedKV
            db_dir = os.path.join(xconfig.DB_DIR, "lmdb")
            map_size = xconfig.get_system_config("lmdb_map_size")
            db_instance = LmdbEnhancedKV(db_dir, map_size=map_size)

        if db_driver == "mysql":
            from xutils.db.driver_mysql import MySQLKV
            sql_logger = xnote_trace.SqlLogger()
            db_instance = MySQLKV(db_instance = xtables.get_db_instance(), sql_logger=sql_logger)
            db_instance.init()
            db_instance.log_debug = xconfig.DatabaseConfig.db_log_debug

            dbutil.RdbSortedSet.init_class(db_instance=xtables.get_db_instance())
            logging.info("use mysql as db engine")

        if db_driver == "ssdb":
            from xutils.db.driver_ssdb import SSDBKV
            db_instance = SSDBKV(host=xconfig.DatabaseConfig.ssdb_host, port=xconfig.DatabaseConfig.ssdb_port)

        # 默认使用leveldb启动
        if db_instance is None:
            try:
                from xutils.db.driver_leveldb import LevelDBImpl
                db_instance = LevelDBImpl(xconfig.DB_DIR, **leveldb_kw)
                db_instance.log_debug = xconfig.DatabaseConfig.db_log_debug
            except ImportError:
                if xutils.is_windows():
                    logging.warning("检测到Windows环境，自动切换到leveldbpy驱动")
                    from xutils.db.driver_leveldbpy import LevelDBProxy
                    db_instance = LevelDBProxy(xconfig.DB_DIR, **leveldb_kw)
                    # 更新驱动名称
                    xconfig.set_global_config("system.db_driver", "leveldbpy")
                else:
                    logging.error("启动失败,请安装leveldb依赖")
                    sys.exit(1)

        dbutil.set_driver_name(db_driver)

        # 是否开启binlog
        binlog = xconfig.DatabaseConfig.binlog
        db_cache = cacheutil.MultiLevelCache()  # 多级缓存：内存+持久化

        # 初始化leveldb数据库
        dbutil.init(xconfig.DB_DIR,
                    db_instance=db_instance,
                    db_cache=db_cache,
                    binlog=binlog,
                    binlog_max_size=xconfig.DatabaseConfig.binlog_max_size)
    except:
        xutils.print_exc()
        logging.error("初始化数据库失败...")
        sys.exit(1)

@log_mem_info_deco("init_kv_engine")
def init_kv_db():
    init_kv_engine()
    xtables_kv.init()

def init_autoreload():

    if not xconfig.WebConfig.fast_reload:
        logging.info("fast_reload is disabled")
        return

    def register_watch(autoreload_thread):
        """监控文件夹及文件的变更"""
        autoreload_thread.watch_dir(xconfig.HANDLERS_DIR, recursive=True)
        autoreload_thread.watch_dir(xconfig.resolve_config_path("static/js"), recursive=True)
        autoreload_thread.watch_dir(xconfig.resolve_config_path("static/css"), recursive=True)
        autoreload_thread.watch_file(xconfig.resolve_config_path("xnote/core/xtemplate.py"))
        for fn in xnote_hooks.HookStore.autoreload_hooks:
            fn(autoreload_thread)

    def reload_callback():
        xnote_code_builder.build()
        # 重新加载handlers目录下的所有模块
        if xconfig.WebConfig.fast_reload:
            xmanager.reload()
        else:
            xmanager.restart()

        autoreload_thread.clear_watched_files()
        register_watch(autoreload_thread)

    # autoreload just reload models
    autoreload_thread = AutoReloadThread(reload_callback)
    register_watch(autoreload_thread)
    autoreload_thread.start()


def init_cluster():
    # 初始化集群配置
    if xconfig.get_system_config("node_role") == "follower":
        logging.info("当前系统以从节点身份运行")


@log_mem_info_deco("init_web_app")
def init_web_app():
    # 关闭autoreload使用自己实现的版本
    var_env = dict()
    app = web.application(list(), var_env, autoreload=False)

    # 初始化模板管理
    xtemplate.init()

    # 初始化主管理器，包括用户及权限、定时任务、各功能模块
    xmanager.init(app, var_env)
    xnote_app = XnoteApp()
    xnote_app.web_app = app
    xnote_app.handler_manager = xmanager.get_handler_manager()
    return xnote_app


def print_env_info():
    cwd = os.getcwd()
    print("当前工作目录:", os.path.abspath(cwd))


def init_debug():
    mem_util.ignore_log_mem_info_deco("db.Get")
    mem_util.ignore_log_mem_info_deco("db.Write")
    mem_util.ignore_log_mem_info_deco("sync_by_binlog_step")


def init_xutils():
    xutils.init(xconfig)
    from xutils.fsutil import FileUtilConfig
    FileUtilConfig.data_dir = xconfig.FileConfig.data_dir
    FileUtilConfig.use_urlencode = xconfig.USE_URLENCODE

def init_app_internal(boot_config_kw=None):
    """初始化APP内部方法"""
    global app
    print_env_info()

    # 构建静态文件
    xnote_code_builder.build()

    # 初始化debug信息
    init_debug()

    # 初始化数据库
    init_sql_db()
    init_kv_db()

    # 初始化工具箱
    init_xutils()

    # 初始化权限系统
    xauth.init()

    # 初始化应用程序
    app = init_web_app()

    # 初始化自动加载功能
    init_autoreload()

    # 初始化集群
    init_cluster()

    # 触发handler里面定义的启动函数
    xmanager.fire("sys.init", None)

    # 注册信号响应
    # 键盘终止信号
    atexit.register(handle_exit)

    # 记录已经启动
    xconfig.mark_started()
    logging.info("app started")

def init_app():
    handle_args_and_init_config()
    return init_app_internal()


def count_worker_thread():
    result = []
    for t in threading.enumerate():
        if t.daemon:
            # 忽略守护线程
            continue
        result.append(t.name)
    return len(result), result


def wait_thread_exit():
    while True:
        count, names = count_worker_thread()
        logging.debug("线程数量:%s", count)
        logging.debug("运行的线程:%s", names)
        if count > 1:
            time.sleep(0.2)
        else:
            return


def run_init_hooks(app):
    for func in xnote_hooks.get_init_hooks():
        func(app)


def main(boot_config_kw=None):
    global app

    # 处理初始化参数
    handle_args_and_init_config(boot_config_kw=boot_config_kw)

    file_lock = FileLock(xconfig.FileConfig.boot_lock_file)

    try:
        if file_lock.acquire():
            # 初始化
            init_app_internal(boot_config_kw=boot_config_kw)
            # 执行钩子函数
            run_init_hooks(app)
            # 监听端口
            app.web_app.run()
            logging.info("服务器已关闭")
            wait_thread_exit()
            sys.exit(xconfig.EXIT_CODE)
        else:
            logging.error("get lock failed")
            logging.error("xnote进程已启动，请不要重复启动!")
            sys.exit(1)
    finally:
        file_lock.release()


if __name__ == '__main__':
    main()
