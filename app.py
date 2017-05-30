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

def get_ip_list(blacklist = []):
    localIp = socket.gethostbyname(socket.gethostname())
    print("localIP:%s" % localIp)
    name, aliaslist, ipList = socket.gethostbyname_ex(socket.gethostname())
    ip_list = []

    for ip in ipList:
        if ip in blacklist:
            continue
        if ip != localIp:
           print("external IP:%s"%ip)
        ip_list.append(ip)

    return ip_list  
    

def check_db():
    xtables.init()

def check_dirs():
    xutils.makedirs(config.DATA_PATH)
    xutils.makedirs(config.LOG_DIR)
    xutils.makedirs("tmp")
        
def handle_data_dir():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="./data")
    args = parser.parse_args(sys.argv[1:])
    config.set_data_path(args.data)
        
def main():
    global app

    port = config.PORT
    
    if not os.environ.get("PORT"):
        os.environ["PORT"] = port

    # 处理Data目录
    handle_data_dir()
    
    var_env = dict()
    
    config.set("host", "localhost")
    config.set("port", port)
    config.set("start_time", time.time())
    # I can reload the system by myself
    app = web.application(list(), var_env, autoreload=False)
    
    # check directories
    check_dirs()
    check_db()

    mgr = xmanager.init(app, var_env)
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
    mgr.run_task()

    app.run()

if __name__ == '__main__':
    main()
