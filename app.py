# encoding=utf-8
import os, socket, sys
import json
import time
import webbrowser
import posixpath
import socket
import logging
import traceback
import argparse

# insert after working dir
sys.path.insert(1, "lib")

import web
import xutils
import xconfig
import xtables
import xmanager

from xutils import *
from autoreload import AutoReloadThread

config = xconfig

def check_db():
    xtables.init()
        
def handle_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="./data")
    parser.add_argument("--delay", default="0")
    parser.add_argument("--ringtone", default="no")
    parser.add_argument("--port", default="1234")
    parser.add_argument("--webbrowser", default="no")
    parser.add_argument("--debug", default="yes")
    parser.add_argument("--minthreads", default="10")
    parser.add_argument("--useCacheSearch", default="no")
    parser.add_argument("--useUrlencode", default="no")
    parser.add_argument("--devMode", default="no")

    web.config.debug = False
    args = parser.parse_args(sys.argv[1:])

    # 处理Data目录
    xconfig.init(args.data)
    # 端口号
    xconfig.PORT = args.port

    # 延迟加载，避免定时任务重复执行
    delay = int(args.delay)
    time.sleep(delay)

    # 启动提醒
    if args.ringtone == "yes":
        xutils.say("系统启动")
    if args.webbrowser == "yes":
        xconfig.OPEN_IN_BROWSER = True
    if args.debug == "yes":
        xconfig.DEBUG = True
        web.config.debug = True
    if args.useCacheSearch == "yes":
        xconfig.USE_CACHE_SEARCH = True
    if args.useUrlencode == "yes":
        xconfig.USE_URLENCODE = True
    if args.devMode == "yes":
        xconfig.DEV_MODE = True

    xconfig.minthreads = int(args.minthreads)
    web.config.minthreads = xconfig.minthreads


def main():
    global app

    handle_args()
    port = config.PORT
    if not os.environ.get("PORT"):
        os.environ["PORT"] = port

    var_env = dict()
    
    config.set("host", "localhost")
    config.set("port", port)
    config.set("start_time", xutils.format_datetime())
    # I can reload the handlers by myself
    app = web.application(list(), var_env, autoreload=False)
    
    check_db()

    # 最后的mapping，用于匹配优先级较低的处理器
    last_mapping = (r"/tools/(.*)", "handlers.tools.tools.handler")
    mgr = xmanager.init(app, var_env, last_mapping = last_mapping)
    mgr.reload()

    def stop_callback():
        # app.stop()
        mgr.reload()
        autoreload_thread.clear_watched_files()
        # autoreload_thread.watch_dir("template")
        autoreload_thread.watch_dir(config.HANDLERS_DIR, recursive=True)

    # autoreload just reload models
    autoreload_thread = AutoReloadThread(stop_callback)
    autoreload_thread.watch_dir(config.HANDLERS_DIR, recursive=True)
    autoreload_thread.start()
    # 启动定时任务检查
    mgr.run_task()

    if xconfig.OPEN_IN_BROWSER:
        webbrowser.open("http://localhost:1234/")
    app.run()

if __name__ == '__main__':
    main()
